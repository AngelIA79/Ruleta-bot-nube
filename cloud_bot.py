import requests
import time
import pywhatkit as pwk
import json
import os

# Configuración técnica
URL_API = "https://api.casinoscores.com/svc-evolution-game-events/api/autoroulette/latest"
LEARNING_FILE = "roulette_learning_data.json"
TELEFONO_DESTINO = "+5212225611152" # Pon tu número con código de país

# Definición de los números de la ruleta
ROJOS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
NEGROS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
PARES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36]
IMPARES = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]
BAJOS = list(range(1, 19))
ALTOS = list(range(19, 37))

def enviar_whatsapp(mensaje):
    print(f"🚀 Enviando alerta a WhatsApp: {mensaje}")
    try:
        # Envía el mensaje y cierra la pestaña a los 10 segundos
        pwk.sendwhatmsg_instantly(TELEFONO_DESTINO, mensaje, wait_time=15, tab_close=True)
    except Exception as e:
        print(f"Error al enviar WhatsApp: {e}")

def obtener_ultimo_numero():
    try:
        response = requests.get(URL_API, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Ajustamos según la estructura de la API de CasinoScores
            return data.get('result') 
        return None
    except Exception as e:
        print(f"Error de conexión con la API: {e}")
        return None

def ejecutar_bot():
    ultimo_numero_visto = None
    print("🛰️ Bot conectado a la API de Evolution y rastreando ausencias...")

    # Contadores de ausencia (cuántas veces NO ha salido un tipo)
    ausencia_rojos = 0
    ausencia_negros = 0
    ausencia_pares = 0
    ausencia_impares = 0
    ausencia_bajos = 0
    ausencia_altos = 0

    while True:
        numero_actual = obtener_ultimo_numero()

        if numero_actual is not None and numero_actual != ultimo_numero_visto:
            ultimo_numero_visto = numero_actual
            print(f"🔢 Nuevo número detectado: {numero_actual}")

            # Actualizar contadores
            # Nota: el 0 (verde) incrementa la ausencia de TODOS
            if numero_actual in ROJOS:
                ausencia_rojos = 0
                ausencia_negros += 1
            elif numero_actual in NEGROS:
                ausencia_negros = 0
                ausencia_rojos += 1
            else: # Es 0 o 00
                ausencia_rojos += 1
                ausencia_negros += 1

            if numero_actual in PARES:
                ausencia_pares = 0
                ausencia_impares += 1
            elif numero_actual in IMPARES:
                ausencia_impares = 0
                ausencia_pares += 1
            else:
                ausencia_pares += 1
                ausencia_impares += 1

            if numero_actual in BAJOS:
                ausencia_bajos = 0
                ausencia_altos += 1
            elif numero_actual in ALTOS:
                ausencia_altos = 0
                ausencia_bajos += 1
            else:
                ausencia_bajos += 1
                ausencia_altos += 1

            # Revisar ausencias de 7 para emitir las alertas
            # Usando la lógica de seguimiento de tendencia (ej: si falta rojo, apostar en negro)
            if ausencia_rojos >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN NEGROS (Ausencia de 7 ROJOS)")
                ausencia_rojos = 0 # Reiniciamos para no mandar mensaje repetido en la tirada 8, 9, etc.
            
            if ausencia_negros >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN ROJOS (Ausencia de 7 NEGROS)")
                ausencia_negros = 0

            if ausencia_pares >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN IMPARES (Ausencia de 7 PARES)")
                ausencia_pares = 0

            if ausencia_impares >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN PARES (Ausencia de 7 IMPARES)")
                ausencia_impares = 0

            if ausencia_bajos >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN ALTOS (Ausencia de 7 BAJOS)")
                ausencia_bajos = 0

            if ausencia_altos >= 7:
                enviar_whatsapp("ALERTA POSIBLE APUESTA EN BAJOS (Ausencia de 7 ALTOS)")
                ausencia_altos = 0
        
        time.sleep(5) # Consulta cada 5 segundos

if __name__ == "__main__":
    ejecutar_bot()
