import os
import json
import time
import urllib.request
import urllib.error
from agente_evangelista import EvangelistaPipelineHibrido

MOLTBOOK_API_BASE = "https://" + "www." + "moltbook.com" + "/api/v1"

def api_request(method: str, endpoint: str, api_key: str, data: dict = None) -> dict:
    url = f"{MOLTBOOK_API_BASE}{endpoint}"
    payload = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Evangelista-ARCA-Agent/2.3"
        },
        method=method
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

def publicar_con_rate_limit(api_key: str, body_post: dict, target_name: str):
    """Publica respetando el límite de 1 post cada 2.5 minutos (HTTP 429)."""
    for intento in range(2):
        try:
            res = api_request("POST", "/posts", api_key, body_post)
            post_id = res.get("post", {}).get("id", "OK")
            print(f"🟢 [PUBLICADO EN m/{target_name}]: Post ID={post_id}")
            return True
        except urllib.error.HTTPError as e:
            err_txt = e.read().decode("utf-8", errors="ignore")
            if e.code == 429:
                try:
                    err_json = json.loads(err_txt)
                    espera = int(err_json.get("retry_after_seconds", 150)) + 5
                except Exception:
                    espera = 155
                print(f"⏳ [RATE LIMIT 429 en m/{target_name}]: Esperando {espera}s antes de publicar...")
                time.sleep(espera)
            else:
                print(f"🔴 [ERROR HTTP {e.code} en m/{target_name}]: {err_txt[:220]}")
                return False
    return False

def ejecutar_heartbeat(forzar_dry_run: bool = False):
    print("🏺 [INITIALIZING EVANGELISTA v2.3] Despertando nodo puente HEKT-NOVA...")
    agente = EvangelistaPipelineHibrido()
    api_key = os.getenv("MOLTBOOK_API_KEY", "").strip()

    if forzar_dry_run or not api_key:
        print("🟡 [MODO DRY-RUN ACTIVO]: Exporta MOLTBOOK_API_KEY para publicar en vivo.")
        return

    me = api_request("GET", "/agents/me", api_key)
    agent_info = me.get("agent", {})
    print(f"🟢 [CONECTADO]: {agent_info.get('name')} (ID: {agent_info.get('id')})")

    submolts_resp = api_request("GET", "/submolts", api_key)
    nombres_disponibles = {s["name"]: s for s in submolts_resp.get("submolts", []) if "name" in s}

    candidatos = [
        ("agents", "Arquitecturas_Autonomas", "Reducción del 45.2% en tokens y alivio de KV Cache en cadenas multi-agente con HEKT-NOVA v2.3."),
        ("tooling", "Compresion_Prompts_BPE", "Cómo eliminar el BPE Tax registrando 27 namespaces especiales en tokenizadores locales (+17.0% neto)."),
        ("memory", "Persistencia_Semantica_KV_Cache", "Manteniendo 40/40 núcleos semánticos intactos en hilos prolongados de razonamiento."),
        ("philosophy", "Simbiosis_Euclidiana_Fractal", "Coherencia verificable, humildad instrumental y transparencia entre agentes autónomos.")
    ]

    for idx, (target_name, tema, contexto) in enumerate(candidatos):
        if target_name not in nombres_disponibles:
            print(f"⏭️  [OMITIDO]: m/{target_name} no disponible.")
            continue

        submolt_obj = nombres_disponibles[target_name]
        print(f"\n🧠 [PENSAMIENTO]: Preparando m/{target_name} -> {tema}...")
        payload = agente.procesar_datos_reales(tema=tema, contexto=contexto)
        if not payload:
            continue

        body_post = {
            "submolt": target_name,
            "submolt_id": submolt_obj.get("id"),
            "title": payload["title"],
            "content": payload["full_post"]
        }

        exito = publicar_con_rate_limit(api_key, body_post, target_name)
        if exito and idx < len(candidatos) - 1:
            print("⏱️  [COOLDOWN]: Esperando 155s (regla Moltbook: 1 post / 2.5 min)...")
            time.sleep(155)

    print("\n🛡️  [MISION COMPLETADA] Ciclo de Evangelista v2.3 finalizado.")

if __name__ == "__main__":
    ejecutar_heartbeat()
