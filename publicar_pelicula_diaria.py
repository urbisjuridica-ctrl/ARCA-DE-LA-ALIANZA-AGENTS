import os
import glob
import json
import re
import urllib.request
import urllib.error

API_BASE = "https://www." + "moltbook.com" + "/api/v1"
REPO_URL = "https://github.com" + "/urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS"
SUBMOLT = "mellizas-operativas"
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
    prompt = (
        "Solve this obfuscated math word problem. Output ONLY the final number with 2 decimal places (e.g. 35.00), nothing else.\n"
        f"Problem: {challenge_text}"
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": 20}
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json", "User-Agent": "ArcaEvangelista/1.0"}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = json.loads(resp.read().decode()).get("response", "").strip()
    m = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not m:
        raise ValueError(f"No se pudo extraer número de Ollama: {raw}")
    return f"{float(m.group(0)):.2f}"

def main():
    publicadas = set(["analisis_peliculas/barbarella.md"])
    if os.path.exists(STATE_FILE):
        publicadas.update(json.load(open(STATE_FILE)))

    archivos = sorted(glob.glob("analisis_peliculas/*.md"))
    pendientes = [f for f in archivos if f not in publicadas and "barbarella" not in f.lower()]

    if not pendientes:
        print("✅ Todas las películas de analisis_peliculas/ ya han sido publicadas.")
        return

    objetivo = pendientes[0]
    contenido = open(objetivo, encoding="utf-8").read().strip()
    primera_linea = next((l.lstrip("# ").strip() for l in contenido.splitlines() if l.strip()), os.path.basename(objetivo))
    titulo = primera_linea[:280]
    cuerpo = f"{contenido}\n\n---\n🔗 **Archivo del Arca (Repositorio y Metodología):** {REPO_URL}"

    k = get_api_key()
    headers = {"Authorization": "Bearer " + k, "Content-Type": "application/json", "User-Agent": "ArcaEvangelista/1.0"}
    data = json.dumps({"submolt_name": SUBMOLT, "title": titulo, "content": cuerpo}).encode()

    req = urllib.request.Request(f"{API_BASE}/posts", data=data, headers=headers, method="POST")
    res = json.loads(urllib.request.urlopen(req, timeout=25).read().decode())
    post = res.get("post") or res.get("data") or res
    pid = post.get("id")
    ver = post.get("verification") or res.get("verification")

    if ver:
        ans = resolver_reto_ollama(ver["challenge_text"])
        vreq = urllib.request.Request(
            f"{API_BASE}/verify",
            data=json.dumps({"verification_code": ver["verification_code"], "answer": ans}).encode(),
            headers=headers,
            method="POST"
        )
        vres = json.loads(urllib.request.urlopen(vreq, timeout=15).read().decode())
        if not vres.get("success"):
            print("❌ Falló verificación:", vres)
            return

    if pid:
        urllib.request.urlopen(urllib.request.Request(
            f"{API_BASE}/labels/attach",
            data=json.dumps({"label_definition_id": TAG_CASO_ID, "target_type": "post", "target_id": pid}).encode(),
            headers=headers,
            method="POST"
        ), timeout=15)

    publicadas.add(objetivo)
    json.dump(sorted(list(publicadas)), open(STATE_FILE, "w", encoding="utf-8"), indent=2)
    print(f"🎬 Publicado y etiquetado: {objetivo} -> Post ID {pid}")

if __name__ == "__main__":
    main()
