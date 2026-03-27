import time
import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

# --- CÓDIGO DE META CLOUD API ---
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN") # Contraseña puente con FB

# --- CONFIGURACIÓN DE RULETA ---
URL_API = "https://api.casinoscores.com/svc-evolution-game-events/api/autoroulette/latest"

ROJOS = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
NEGROS = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
PARES = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36]
IMPARES = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35]
BAJOS = list(range(1, 19))
ALTOS = list(range(19, 37))

# Estado Global del Bot
tracking_active = False
usuario_destino = ""

def enviar_mensaje_whatsapp(numero_destino, mensaje):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    print(f"📤 Intentando enviar mensaje a {numero_destino}...", flush=True)
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": mensaje}
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            print(f"📲 Alerta enviada con éxito. Código: {response.getcode()}", flush=True)
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}", flush=True)

def obtener_ultimo_numero():
    try:
        req = urllib.request.Request(URL_API, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('result') 
        return None
    except Exception as e:
        print(f"Error de conexión con la API de Ruleta: {e}", flush=True)
        return None

def rastreador_ruleta():
    global tracking_active, usuario_destino
    ultimo_numero_visto = None
    ausencia_rojos = 0
    ausencia_negros = 0
    ausencia_pares = 0
    ausencia_impares = 0
    ausencia_bajos = 0
    ausencia_altos = 0

    while True:
        if tracking_active and usuario_destino:
            numero_actual = obtener_ultimo_numero()
            if numero_actual is not None and numero_actual != ultimo_numero_visto:
                ultimo_numero_visto = numero_actual
                print(f"🔢 Cayó: {numero_actual}", flush=True)
                if numero_actual in ROJOS:
                    ausencia_rojos = 0
                    ausencia_negros += 1
                elif numero_actual in NEGROS:
                    ausencia_negros = 0
                    ausencia_rojos += 1
                else: 
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

                # Alertas de 7 rachas
                if ausencia_rojos >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN NEGROS (Ausencia de 7 ROJOS)")
                    ausencia_rojos = 0
                if ausencia_negros >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN ROJOS (Ausencia de 7 NEGROS)")
                    ausencia_negros = 0
                if ausencia_pares >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN IMPARES (Ausencia de 7 PARES)")
                    ausencia_pares = 0
                if ausencia_impares >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN PARES (Ausencia de 7 IMPARES)")
                    ausencia_impares = 0
                if ausencia_bajos >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN ALTOS (Ausencia de 7 BAJOS)")
                    ausencia_bajos = 0
                if ausencia_altos >= 7:
                    enviar_mensaje_whatsapp(usuario_destino, "ALERTA POSIBLE APUESTA EN BAJOS (Ausencia de 7 ALTOS)")
                    ausencia_altos = 0
        time.sleep(5) 

class WebhookHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/webhook':
            query_params = parse_qs(parsed_url.query)
            mode = query_params.get("hub.mode", [""])[0]
            token = query_params.get("hub.verify_token", [""])[0]
            challenge = query_params.get("hub.challenge", [""])[0]

            if mode and token:
                if mode == "subscribe" and token == VERIFY_TOKEN:
                    print(f"🟢 ¡WEBHOOK ACTIVADO! Enviando challenge: {challenge}", flush=True)
                    response_payload = challenge.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Length', str(len(response_payload)))
                    self.end_headers()
                    self.wfile.write(response_payload)
                    return
                else:
                    print(f"❌ Fallo de verificación de Token. Recibido: {token}", flush=True)
                    self.send_response(403)
                    self.end_headers()
                    return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hola! El Bot Ruleta corre sin dependencias.")

    def do_POST(self):
        global tracking_active, usuario_destino
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
                print(f"📩 Webhook recibido: {post_data[:200]}...", flush=True)
                try:
                    body = json.loads(post_data)
                    if body.get("object"):
                        for entry in body.get("entry", []):
                            for change in entry.get("changes", []):
                                value = change.get("value", {})
                                if "messages" in value:
                                    msg = value["messages"][0]
                                    remitente = msg.get("from")
                                    texto = msg.get("text", {}).get("body", "").strip().lower()
                                    
                                    print(f"💬 Mensaje de {remitente}: {texto}", flush=True)

                                    if texto == "start":
                                        tracking_active = True
                                        usuario_destino = remitente
                                        print(f"⚡ INICIANDO rastreador para {remitente}", flush=True)
                                        enviar_mensaje_whatsapp(remitente, "✅ RuletaBot se ha INICIADO y trabaja desde La Nube. Avisándote en ausencias de 7.")
                                    
                                    elif texto == "stop":
                                        tracking_active = False
                                        print(f"🛑 PAUSANDO rastreador por orden de {remitente}", flush=True)
                                        enviar_mensaje_whatsapp(remitente, "🛑 RuletaBot se ha PAUSADO.")
                except Exception as e:
                    print(f"❌ Error procesando datos del Webhook: {e}", flush=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"EVENTO RECIBIDO")

if __name__ == "__main__":
    hilo = threading.Thread(target=rastreador_ruleta, daemon=True)
    hilo.start()
    
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"🚀 Servidor nativo corriendo en puerto {port}", flush=True)
    server.serve_forever()
