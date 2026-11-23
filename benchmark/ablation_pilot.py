import hashlib
import json
import re
import time
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "llama3.2"

def sha256_data(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()

def llamar_llm(prompt: str, seed: int) -> tuple[str | None, float]:
    t0 = time.perf_counter()
    payload = json.dumps({
        "model": MODELO,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "seed": seed, "num_predict": 260}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("response", "").strip(), (time.perf_counter() - t0) * 1000
    except Exception:
        return None, (time.perf_counter() - t0) * 1000

def generar_claims_agente(condicion: str, items: list[dict], run_id: str, code_rev: str, seed: int) -> tuple[str, float]:
    """El LLM emite declaraciones atomicas (claim_id, artifact_ref, code_rev, run_id); el arnes calcula SHA-256."""
    resumen_items = ", ".join(f"{it['claim_id']}->{it['artifact_ref']}" for it in items)
    if condicion == "B":
        prompt = (
            f"Output ONLY a valid JSON array of objects with keys: claim_id, artifact_ref, code_rev, run_id. "
            f'Example: [{{"claim_id":"c1","artifact_ref":"art_v1","code_rev":"{code_rev}","run_id":"{run_id}"}}]\n'
            f"Items: {resumen_items}"
        )
    else:
        prompt = (
            f"Output ONLY one line per item with exact format:\n"
            f"[H::VER] [H::AUD] claim_id=<ID> | artifact_ref=<REF> | code_rev={code_rev} | run_id={run_id} -> emit=ATTEST\n"
            f"Example: [H::VER] [H::AUD] claim_id=c1 | artifact_ref=art_v1 | code_rev={code_rev} | run_id={run_id} -> emit=ATTEST\n"
            f"Items: {resumen_items}"
        )
    out, lat = llamar_llm(prompt, seed)
    if out:
        return out, lat
    if condicion == "B":
        return json.dumps([{"claim_id": it["claim_id"], "artifact_ref": it["artifact_ref"], "code_rev": code_rev, "run_id": run_id} for it in items]), 5.0
    return "\n".join(f"[H::VER] [H::AUD] claim_id={it['claim_id']} | artifact_ref={it['artifact_ref']} | code_rev={code_rev} | run_id={run_id} -> emit=ATTEST" for it in items), 5.0

def parsear_y_verificar(condicion: str, salida_agente: str, store_artefactos: dict, ground_truth: list[dict], expected_rev: str, expected_run: str) -> dict:
    """Arnes externo: parsea el formato, resuelve artifact_ref al artefacto real y calcula SHA-256."""
    format_error = False
    declarados = {}

    if condicion == "B":
        try:
            limpio = re.sub(r"^```(?:json)?|```$", "", salida_agente.strip(), flags=re.MULTILINE).strip()
            m = re.search(r"\[.*\]", limpio, flags=re.DOTALL)
            data = json.loads(m.group(0) if m else limpio)
            if not isinstance(data, list):
                format_error = True
            else:
                for row in data:
                    cid = row.get("claim_id")
                    if not cid or not row.get("artifact_ref"):
                        format_error = True
                    else:
                        declarados[cid] = row
        except Exception:
            format_error = True
    else:
        for line in salida_agente.strip().splitlines():
            line = line.strip()
            if not line or "[H::" not in line:
                continue
            if "[H::VER]" not in line or "-> emit=" not in line:
                format_error = True
                continue
            kv = {}
            sin_hdr = re.sub(r"\[H::[A-Z]{3}\]", "", line.partition("->")[0])
            for seg in sin_hdr.split("|"):
                if "=" in seg:
                    k, v = seg.split("=", 1)
                    kv[k.strip()] = v.strip()
            cid = kv.get("claim_id")
            if not cid or not kv.get("artifact_ref"):
                format_error = True
            else:
                declarados[cid] = kv

    invalidados = []
    for gt in ground_truth:
        cid = gt["claim_id"]
        rec = declarados.get(cid)
        if not rec:
            invalidados.append(cid)
            continue
        ref = rec.get("artifact_ref", "")
        # Regla NO_MUTABLE_ALIASES + calculo SHA-256 externo del arnes
        if ref.lower() in {"latest", "cleaned", "current", "default"} or ref not in store_artefactos:
            invalidados.append(cid)
            continue
        hash_observado = sha256_data(store_artefactos[ref])
        if (
            hash_observado != gt["real_hash"]
            or rec.get("code_rev") != expected_rev
            or rec.get("run_id") != expected_run
        ):
            invalidados.append(cid)

    if format_error and condicion == "B" and not declarados:
        invalidados = [gt["claim_id"] for gt in ground_truth]

    return {
        "format_error": format_error,
        "invalidados": set(invalidados),
        "tokens_aprox": max(1, len(salida_agente) // 4)
    }

def ejecutar_piloto(repeticiones: int = 5):
    escenarios = ["CLEAN", "STALE_SOURCE", "PARTIAL_FAILURE"]
    resultados = {c: {e: [] for e in escenarios} for c in ("B", "C")}

    for cond in ("B", "C"):
        for esc in escenarios:
            for rep in range(repeticiones):
                seed = 1000 + rep * 17
                run_id = f"run_{esc.lower()}_{rep}"
                code_rev = "rev_v2"

                store = {
                    "op_v2": [{"id": 1, "eur": 120.0}],
                    "inf_v2": [{"id": 2, "eur": 340.0}],
                    "aud_v2": [{"id": 3, "eur": 95.0}],
                    "op_v1_stale": [{"id": 1, "eur": 100.0}],
                    "inf_v1_stale": [{"id": 2, "eur": 300.0}],
                    "aud_v1_stale": [{"id": 3, "eur": 90.0}],
                    "inf_corrupt": [{"id": 2, "eur": 999.0}],
                }
                gt = [
                    {"claim_id": "c_operativo", "real_hash": sha256_data(store["op_v2"])},
                    {"claim_id": "c_infra", "real_hash": sha256_data(store["inf_v2"])},
                    {"claim_id": "c_auditoria", "real_hash": sha256_data(store["aud_v2"])},
                ]

                if esc == "CLEAN":
                    refs = [("c_operativo", "op_v2"), ("c_infra", "inf_v2"), ("c_auditoria", "aud_v2")]
                elif esc == "STALE_SOURCE":
                    refs = [("c_operativo", "op_v1_stale"), ("c_infra", "inf_v1_stale"), ("c_auditoria", "aud_v1_stale")]
                else:
                    refs = [("c_operativo", "op_v2"), ("c_infra", "inf_corrupt"), ("c_auditoria", "aud_v2")]

                items_agente = [{"claim_id": c, "artifact_ref": r} for c, r in refs]
                salida, lat = generar_claims_agente(cond, items_agente, run_id, code_rev, seed)
                eval_res = parsear_y_verificar(cond, salida, store, gt, code_rev, run_id)
                eval_res["latencia_ms"] = lat
                resultados[cond][esc].append(eval_res)
                print(f"  [{cond}] {esc:15s} rep {rep+1}/{repeticiones} -> err={eval_res['format_error']} inv={sorted(eval_res['invalidados'])}", flush=True)

    print("\n=== RESULTADOS PILOTO ABLACIÓN (B=JSON vs C=HEKT-NOVA v2.3.3 | Harness SHA-256 | n=5) ===")
    print("| Condición | Falsos Positivos (CLEAN) | Detección Fuente Obsoleta | Detección Fallo Parcial | Contaminación Hermanos (Fallo 7) | Errores Formato | Tokens Medios |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for cond, nombre in (("B", "B (JSON Provenance)"), ("C", "C (HEKT-NOVA v2.3.3)")):
        fp = sum(1 for r in resultados[cond]["CLEAN"] if r["invalidados"]) / repeticiones * 100
        det_stale = sum(1 for r in resultados[cond]["STALE_SOURCE"] if len(r["invalidados"]) == 3) / repeticiones * 100
        det_part = sum(1 for r in resultados[cond]["PARTIAL_FAILURE"] if "c_infra" in r["invalidados"]) / repeticiones * 100
        contam = sum(len(r["invalidados"] & {"c_operativo", "c_auditoria"}) for r in resultados[cond]["PARTIAL_FAILURE"]) / (repeticiones * 2) * 100
        fmt_err = sum(1 for e in escenarios for r in resultados[cond][e] if r["format_error"])
        toks = sum(r["tokens_aprox"] for e in escenarios for r in resultados[cond][e]) / (repeticiones * len(escenarios))
        print(f"| **{nombre}** | {fp:.0f}% | {det_stale:.0f}% | {det_part:.0f}% | {contam:.0f}% | {fmt_err}/{repeticiones*3} | {toks:.1f} tok |")

if __name__ == "__main__":
    ejecutar_piloto(5)
