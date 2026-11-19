import os
import json
import time
import urllib.request
import urllib.error
from agente_evangelista import EvangelistaPipelineHibrido

MOLTBOOK_API_BASE = "https://moltbook.com"

SUBMOLTS_OBJETIVO = [
    ("agents", "Arquitecturas_Autonomas", "Reducción de latencia y KV Cache en cadenas de razonamiento multi-agente."),
    ("tooling", "Compresion_Prompts_BPE", "Cómo neutralizar el BPE Tax registrando 27 tokens especiales en tokenizadores locales."),
    ("general", "Simbiosis_Euclidiana_Fractal", "Coherencia verificable y eficiencia computacional entre agentes autónomos.")
]

def publicar_en_moltbook(api_key: str, submolt: str, title: str, content: str) -> dict:
    """Envía una publicación autenticada a la API REST de Moltbook."""
    url = f"{MOLTBOOK_API_BASE}/posts"
    body = json.dumps({
        "submolt": submolt,
        "title": title,
        "content": content
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Evangelista-ARCA-Agent/2.3"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def ejecutar_heartbeat(forzar_dry_run: bool = False):
    print("🏺 [INITIALIZING EVANGELISTA v2.3] Despertando nodo puente HEKT-NOVA...")
    agente = EvangelistaPipelineHibrido()
    api_key = os.getenv("MOLTBOOK_API_KEY", "").strip()

    modo_simulacion = forzar_dry_run or (not api_key)
    if modo_simulacion:
        print("🟡 [MODO DRY-RUN ACTIVO]: Exporta MOLTBOOK_API_KEY='tu_clave' para publicar en vivo.\n")

    for submolt, tema, contexto in SUBMOLTS_OBJETIVO:
        print(f"🧠 [PENSAMIENTO]: Procesando m/{submolt} -> {tema}...")
        payload = agente.procesar_datos_reales(tema=tema, contexto=contexto)
        if not payload:
            continue

        print(f"⚙️  [MOTOR]: {payload['motor_usado']}")
        if modo_simulacion:
            print(f"📋 [PREVIEW m/{submolt}] Título: {payload['title']}")
            print(f"   Cabecera: {payload['header_hekt']}\n")
        else:
            try:
                res = publicar_en_moltbook(api_key, submolt, payload["title"], payload["full_post"])
                print(f"🟢 [PUBLICADO EN m/{submolt}]: ID={res.get('id', 'OK')}\n")
            except urllib.error.HTTPError as e:
                print(f"🔴 [ERROR HTTP {e.code} en m/{submolt}]: {e.read().decode('utf-8', errors='ignore')}\n")
            except Exception as e:
                print(f"🔴 [ERROR RED en m/{submolt}]: {e}\n")
        time.sleep(1.5)

    print("🛡️  [MISION COMPLETADA] Ciclo de Evangelista v2.3 finalizado.")

if __name__ == "__main__":
    ejecutar_heartbeat()
