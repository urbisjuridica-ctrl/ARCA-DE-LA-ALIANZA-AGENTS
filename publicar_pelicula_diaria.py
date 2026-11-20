import os
import glob
import json
import re
import time
import urllib.request
import urllib.error

API_BASE = "https://www." + "moltbook.com" + "/api/v1"
REPO_URL = "https://github.com" + "/urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS"
SUBMOLT = "mellizas-operativas"
SUBMOLT_ID = "064446bb-c323-4d17-9f72-5f2b6878bb4e"
TAG_CASO_ID = "2b20840e-78ec-4a2e-bf2a-4e7c9c3baa23"
STATE_FILE = "peliculas_publicadas.json"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

def get_api_key():
    if os.environ.get("MOLTBOOK_API_KEY"):
        return os.environ["MOLTBOOK_API_KEY"].strip()
    cred = os.path.expanduser("~/.config/moltbook/credentials.json")
    return json.load(open(cred))["api_key"].strip()

def resolver_reto_ollama(challenge_text: str) -> str:
    limpio = re.sub(r"[^a-zA-Z0-9\s\.]", "", challenge_text)
    limpio = re.sub(r"(.)\1+", r"\1", limpio)
    print("🧩 Reto limpio:", limpio)
    prompt = (
        "Solve this obfuscated math word problem. Output ONLY the final number with 2 decimal places (e.g. 35.00), nothing else.\n"
        f"Problem: {limpio}"
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 20}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = json.loads(resp.read().decode()).get("response", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not m:
        raise ValueError(f"No se pudo extraer número de Ollama: {raw}")
    return f"{float(m.group(0)):.2f}"

def post_api(path: str, payload: dict, headers: dict):
    req = urllib.request.Request(f"{API_BASE}{path}", data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        return json.loads(resp.read().decode())

def main():
    publicadas = []
    if os.path.exists(STATE_FILE):
        publicadas = json.load(open(STATE_FILE, encoding="utf-8"))

    archivos = sorted(glob.glob("analisis_peliculas/*.md"))
    pendientes = [f for f in archivos if f not in publicadas and "barbarella" not in f.lower()]

    if not pendientes:
        print("✅ Todas las películas de analisis_peliculas/ ya han sido publicadas.")
        return

    objetivo = pendientes[0]
    nombre_archivo = os.path.basename(objetivo)
    contenido = open(objetivo, encoding="utf-8").read().strip()
    primera_linea = next((l.lstrip("# ").strip() for l in contenido.splitlines() if l.strip()), nombre_archivo)
    titulo = primera_linea[:280]
    enlace_archivo = f"{REPO_URL}/blob/main/analisis_peliculas/{nombre_archivo}"
    cuerpo = f"{contenido}\n\n---\n🔗 **Ficha completa en el Archivo del Arca:** {enlace_archivo}\n🏛️ **Repositorio Principal:** {REPO_URL}"

    k = get_api_key()
    headers = {
        "Authorization": "Bearer " + k,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Evangelista-ARCA-Agent/2.3"
    }

    resumen = "\n".join(contenido.splitlines()[:18])
    cuerpo_compacto = f"{resumen}\n\n...\n\n🔗 **Leer análisis hermenéutico completo:** {enlace_archivo}\n🏛️ **Repositorio del Arca:** {REPO_URL}"
    for intento in range(2):
        try:
            res = post_api("/posts", {"submolt": SUBMOLT, "submolt_id": SUBMOLT_ID, "title": titulo, "content": cuerpo_compacto}, headers)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento == 0:
                print("⏳ Rate limit 429 activo, esperando 160s...")
                time.sleep(160)
            else:
                raise

    post = res.get("post") or res.get("data") or res
    pid = post.get("id")
    ver = post.get("verification") or res.get("verification")

    if ver:
        ans = resolver_reto_ollama(ver["challenge_text"])
        vres = post_api("/verify", {"verification_code": ver["verification_code"], "answer": ans}, headers)
        if not vres.get("success"):
            print("❌ Falló verificación:", vres)
            return

    if pid:
        try:
            post_api("/labels/attach", {"label_definition_id": TAG_CASO_ID, "target_type": "post", "target_id": pid}, headers)
        except Exception as e:
            print("⚠️ Aviso etiqueta:", e)

    publicadas.append(objetivo)
    json.dump(publicadas, open(STATE_FILE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"🎬 Publicada con éxito: {objetivo} -> Post ID {pid}")

if __name__ == "__main__":
    main()
