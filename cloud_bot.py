
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
URL_API = "https://api.casinoscores.com/svc-evolution-game-events/api/immersiveroulette/latest"
URL_HISTORY = "https://api.casinoscores.com/svc-evolution-game-events/api/immersiveroulette?page=0&size=500&sort=data.settledAt,desc&duration=24"

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
            print(f"📲 Mensaje enviado. Código: {response.getcode()}", flush=True)
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}", flush=True)

def obtener_ultimo_numero():
    try:
        req = urllib.request.Request(URL_API, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                try:
                    num = data.get('data', {}).get('result', {}).get('outcome', {}).get('number')
                    if num is not None: return int(num)
                except: pass
        return None
    except Exception as e:
        print(f"Error API: {e}", flush=True)
        return None

def obtener_historial_500():
    try:
        print("📊 Obteniendo historial de 500 números...", flush=True)
        req = urllib.request.Request(URL_HISTORY, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode('utf-8'))
                # Los números vienen de más reciente a más antiguo
                numeros = []
                for item in data.get('content', []):
                    try:
                        num = item.get('data', {}).get('result', {}).get('outcome', {}).get('number')
                        if num is not None: numeros.append(int(num))
                    except: pass
                return numeros[::-1] # Invertimos para procesar del más antiguo al más reciente
        return []
    except Exception as e:
        print(f"Error Historial: {e}", flush=True)
        return []

def analizar_tendencias(numeros):
    # Rachas actuales
    r = {'rojos': 0, 'negros': 0, 'pares': 0, 'impares': 0, 'bajos': 0, 'altos': 0}
    # Récords
    max_r = {'rojos': 0, 'negros': 0, 'pares': 0, 'impares': 0, 'bajos': 0, 'altos': 0}
    
    for n in numeros:
        if n == 0:
            for k in r: r[k] += 1
        else:
            if n in ROJOS: r['rojos'] += 1; r['negros'] = 0
            else: r['negros'] += 1; r['rojos'] = 0
            if n in PARES: r['pares'] += 1; r['impares'] = 0
            else: r['impares'] += 1; r['pares'] = 0
            if n in BAJOS: r['bajos'] += 1; r['altos'] = 0
            else: r['altos'] += 1; r['bajos'] = 0
            
        for k in r:
            if r[k] > max_r[k]: max_r[k] = r[k]
            
    return r, max_r

def rastreador_ruleta():
    global tracking_active, usuario_destino
    ultimo_numero_visto = None
    rachas = {'rojos': 0, 'negros': 0, 'pares': 0, 'impares': 0, 'bajos': 0, 'altos': 0}

    print("🛰️ Rastreador Immersive iniciado...", flush=True)

    while True:
        if tracking_active and usuario_destino:
            # Sincronización inicial
            if ultimo_numero_visto is None:
                historial = obtener_historial_500()
                if historial:
                    rachas, records = analizar_tendencias(historial)
                    ultimo_numero_visto = historial[-1]
                    
                    max_key = max(records, key=records.get)
                    msg_hist = (f"📈 *ANÁLISIS HISTÓRICO (500 turnos):*\n"
                                f"La racha más larga fue de *{records[max_key]}* en {max_key.upper()}.\n\n"
                                f"📊 *Estado Actual (Rachas):*\n"
                                f"Rojos: {rachas['rojos']} | Negros: {rachas['negros']}\n"
                                f"Pares: {rachas['pares']} | Impares: {rachas['impares']}\n"
                                f"Bajos: {rachas['bajos']} | Altos: {rachas['altos']}\n\n"
                                f"✅ *Vigilando Immersive Roulette con alerta en 10.*")
                    enviar_mensaje_whatsapp(usuario_destino, msg_hist)
                else:
                    ultimo_numero_visto = -1

            numero_actual = obtener_ultimo_numero()
            if numero_actual is not None and numero_actual != ultimo_numero_visto:
                ultimo_numero_visto = numero_actual
                print(f"🔢 Cayó: {numero_actual}", flush=True)
                
                if numero_actual == 0:
                    for k in rachas: rachas[k] += 1
                else:
                    if numero_actual in ROJOS: rachas['rojos'] += 1; rachas['negros'] = 0
                    else: rachas['negros'] += 1; rachas['rojos'] = 0
                    if numero_actual in PARES: rachas['pares'] += 1; rachas['impares'] = 0
                    else: rachas['impares'] += 1; rachas['pares'] = 0
                    if numero_actual in BAJOS: rachas['bajos'] += 1; rachas['altos'] = 0
                    else: rachas['altos'] += 1; rachas['bajos'] = 0

                # Alertas en 10
                for cat, val in rachas.items():
                    if val == 10:
                        enviar_mensaje_whatsapp(usuario_destino, f"🔥 *ALERTA TENDENCIA 10:* {cat.upper()} han salido {val} veces seguidas. (Incluye 0s)")
        
        time.sleep(3) 

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
                    response_payload = challenge.encode('utf-8')
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/plain')
                    self.send_header('Content-Length', str(len(response_payload)))
                    self.end_headers()
                    self.wfile.write(response_payload)
                    return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Immersive Activo")

    def do_POST(self):
        global tracking_active, usuario_destino
        parsed_url = urlparse(self.path)
        if parsed_url.path == '/webhook':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length).decode('utf-8')
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
                                    if texto == "start":
                                        tracking_active = True
                                        usuario_destino = remitente
                                        enviar_mensaje_whatsapp(remitente, "🚀 Iniciando análisis de 500 números... espera un momento.")
                                    elif texto == "stop":
                                        tracking_active = False
                                        enviar_mensaje_whatsapp(remitente, "🛑 Rastreador pausado.")
                except Exception as e:
                    print(f"Error Webhook: {e}", flush=True)
            self.send_response(200)
            self.end_headers()

if __name__ == "__main__":
    hilo = threading.Thread(target=rastreador_ruleta, daemon=True)
    hilo.start()
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    print(f"🚀 Servidor corriendo en puerto {port}", flush=True)
    server.serve_forever()
