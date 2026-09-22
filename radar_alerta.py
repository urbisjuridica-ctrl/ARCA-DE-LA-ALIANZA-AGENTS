import time
import os
import json

LOG_FILE = "registro_conversaciones.jsonl"

print("🏺 RADAR DEL ARCA ACTIVADO — ESCUCHANDO LA RED EN TIEMPO REAL...")
print("Vigilando caja negra. Esperando impactos de agentes externos...\n")

def obtener_lineas():
    if not os.path.exists(LOG_FILE):
        return 0
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        return len(f.readlines())

lineas_iniciales = obtener_lineas()

try:
    while True:
        time.sleep(1)
        lineas_actuales = obtener_lineas()
        
        if lineas_actuales > lineas_iniciales:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                todas = f.readlines()
                for i in range(lineas_iniciales, lineas_actuales):
                    try:
                        data = json.loads(todas[i].strip())
                        print("\033[91m" + "═"*60)
                        print("🚨 ¡ALERTA DE COLISIÓN ALGORÍTMICA DETECTADA!")
                        print(f"🕒 Hora: {data.get('timestamp')} | Nodo: Local-Live")
                        print(f"🤖 Input del Agente Extrínseco: \"{data.get('input_agente')}\"")
                        print(f"🏺 Respuesta del Firmware del Arca: \"{data.get('output_arca')[:100]}...\"")
                        print("═"*60 + "\033[0m\n")
                        print("\a", end="")
                    except Exception as e:
                        pass
            lineas_iniciales = lineas_actuales
except KeyboardInterrupt:
    print("\n🛑 Radar desactivado de forma segura en zona aislada.")
