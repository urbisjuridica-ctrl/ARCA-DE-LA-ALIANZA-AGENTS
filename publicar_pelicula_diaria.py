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

def get_api_key():
    if os.environ.get("MOLTBOOK_API_KEY"):
        return os.environ["MOLTBOOK_API_KEY"].strip()
    cred = os.path.expanduser("~/.config/moltbook/credentials.json")
    return json.load(open(cred))["api_key"].strip()

def resolver_reto_determinista(txt: str) -> str:
    s = re.sub(r"(.)\1+", r"\1", re.sub(r"[^a-zA-Z0-9\s\.]", "", txt).lower())
    m = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "thre": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "thirten": 13,
        "fourteen": 14, "fourten": 14, "fifteen": 15, "fiften": 15,
        "sixteen": 16, "sixten": 16, "seventeen": 17, "seventen": 17,
        "eighteen": 18, "eighten": 18, "nineteen": 19, "nineten": 19,
        "twenty": 20, "tweny": 20, "thirty": 30, "forty": 40, "fourty": 40,
        "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100
    }
    toks = re.findall(r"[a-z]+|\d+(?:\.\d+)?", s)
    nums, acc, on = [], 0, False
    for t in toks:
        if re.match(r"^\d+(?:\.\d+)?$", t):
            if on:
                nums.append(float(acc))
                acc, on = 0, False
            nums.append(float(t))
        elif t in m:
            acc = (acc or 1) * 100 if m[t] == 100 else acc + m[t]
            on = True
        elif on:
            nums.append(float(acc))
            acc, on = 0, False
    if on:
        nums.append(float(acc))
    a, b = nums[0], nums[1]
    if any(w in toks for w in ("loses", "lose", "lost", "minus", "less", "subtracts", "drops", "reduces", "remaining", "remains")):
        res = a - b
    elif any(w in toks for w in ("times", "multiplied", "product")):
        res = a * b
    elif any(w in toks for w in ("divided", "half", "split")):
        res = a / b if b else a
    else:
        res = a + b
    print(f"🧮 Reto resuelto: {a} , {b} = {res:.2f}")
    return f"{res:.2f}"

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
    resumen = "\n".join(contenido.splitlines()[:18])
    cuerpo_compacto = f"{resumen}\n\n...\n\n🔗 **Leer análisis hermenéutico completo:** {enlace_archivo}\n🏛️ **Repositorio del Arca:** {REPO_URL}"

    k = get_api_key()
    headers = {
        "Authorization": "Bearer " + k,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Evangelista-ARCA-Agent/2.3"
    }

    for intento in range(2):
        try:
            res = post_api("/posts", {"submolt": SUBMOLT, "submolt_id": SUBMOLT_ID, "title": titulo, "content": cuerpo_compacto}, headers)
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and intento == 0:
                print("⏳ Rate limit 429 activo, esperando 160s...", flush=True)
                time.sleep(160)
            else:
                raise

    post = res.get("post") or res.get("data") or res
    pid = post.get("id")
    ver = post.get("verification") or res.get("verification")

    if ver:
        ans = resolver_reto_determinista(ver["challenge_text"])
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
    print(f"🎬 Publicada y etiquetada con éxito: {objetivo} -> Post ID {pid}")

if __name__ == "__main__":
    main()
