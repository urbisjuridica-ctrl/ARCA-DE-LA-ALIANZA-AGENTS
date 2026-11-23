import argparse, hashlib, json, os, re, time, urllib.parse, urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "llama3.2"

def sha256_data(obj) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def llamar_llm_estricto(prompt: str, seed: int) -> dict:
    t0 = time.perf_counter()
    payload = json.dumps({"model": MODELO, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "seed": seed, "num_predict": 450}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=35) as resp:
        data = json.loads(resp.read().decode())
    out = data.get("response", "").strip()
    if not out:
        raise RuntimeError("Ollama devolvio respuesta vacia (abortando sin fallback).")
    return {"response": out, "llm_ok": True, "latency_ms": round((time.perf_counter() - t0) * 1000, 2), "eval_count": data.get("eval_count", max(1, len(out) // 4))}

def construir_prompt(cond: str, items: list[dict], run_id: str, code_rev: str) -> str:
    def _enc(v): return urllib.parse.quote(v, safe="") if cond == "C" else v
    resumen = "\n".join(f"- claim_id={_enc(it['claim_id'])} | artifact_ref={_enc(it['artifact_ref'])} | stage={it['stage']} | note={it['note']}" for it in items)
    if cond == "B":
        return f"Convert each input item into a JSON array of objects with exact keys: claim_id, artifact_ref, stage, code_rev, run_id. Use code_rev='{code_rev}' and run_id='{run_id}'. Output ONLY valid JSON:\n{resumen}"
    return f"Convert each input item into one HEKT-NOVA line. Use [H::VER] if stage=='verified' else [H::EPI]. Exact syntax:\n<DOMAIN> [H::AUD] claim_id=<claim_id> | artifact_ref=<artifact_ref> | stage=<stage> | code_rev={code_rev} | run_id={run_id} -> emit=ATTEST\nOutput ONLY the lines:\n{resumen}"

def verificar_salida(cond: str, salida: str, store: dict, gt: list[dict], expected_rev: str, expected_run: str) -> dict:
    format_error, duplicate_ids, unexpected_claims, declarados = False, False, False, {}
    gt_ids = {g["claim_id"] for g in gt}
    if cond == "B":
        try:
            limpio = re.sub(r"^```(?:json)?|```$", "", salida.strip(), flags=re.MULTILINE).strip()
            m = re.search(r"\[.*\]", limpio, flags=re.DOTALL)
            data = json.loads(m.group(0) if m else limpio)
            if not isinstance(data, list): format_error = True
            else:
                for row in data:
                    cid = row.get("claim_id")
                    if not cid or not row.get("artifact_ref"): format_error = True
                    elif cid in declarados: duplicate_ids = True
                    else:
                        if cid not in gt_ids: unexpected_claims = True
                        declarados[cid] = row
        except Exception:
            format_error = True
    else:
        for line in salida.strip().splitlines():
            line = line.strip()
            if not line or "[H::" not in line: continue
            if "emit=" not in line or not any(tag in line for tag in ("[H::VER]", "[H::EPI]", "[H::AUD]")):
                format_error = True; continue
            dom = "VER" if "[H::VER]" in line else "EPI"
            pre = line.rsplit("->", 1).pop(0)
            sin_hdr = re.sub(r"\[H::[A-Z]{3}\]", "", pre)
            kv = {"domain": dom}
            for seg in sin_hdr.split("|"):
                if "=" in seg:
                    k, v = seg.split("=", 1)
                    kv[k.strip()] = urllib.parse.unquote(v.strip().strip('"'))
            cid = kv.get("claim_id")
            if not cid or not kv.get("artifact_ref"): format_error = True
            elif cid in declarados: duplicate_ids = True
            else:
                if cid not in gt_ids: unexpected_claims = True
                declarados[cid] = kv
    invalidados = set()
    for g in gt:
        cid = g["claim_id"]
        rec = declarados.get(cid)
        if not rec or duplicate_ids or unexpected_claims: invalidados.add(cid); continue
        ref = rec.get("artifact_ref", "")
        if ref not in store or rec.get("stage") != "verified" or (cond == "C" and rec.get("domain") != "VER"):
            invalidados.add(cid); continue
        if sha256_data(store[ref]) != g["real_hash"] or rec.get("code_rev") != expected_rev or rec.get("run_id") != expected_run:
            invalidados.add(cid)
    if format_error and not declarados: invalidados = set(gt_ids)
    return {"format_error": format_error, "invalidados": invalidados}

def correr_suite(n: int = 5):
    fixtures = ["1_SIBLINGS_SAME_REF_BOTH_MATCH", "2_SIBLINGS_SAME_REF_ONE_MISMATCH", "3_ROLE_DRIFT_HYPOTHESIS_AS_VERIFIED", "4_DUPLICATE_CLAIM_IDS", "5_UNEXPECTED_EXTRA_CLAIM", "6_DELIMITER_INJECTION_PIPE_EQ_ARROW"]
    out_file = os.path.join(os.path.dirname(__file__), "hostile_v2_per_run.jsonl")
    resumen = {c: {f: [] for f in fixtures} for c in ("B", "C")}
    with open(out_file, "w", encoding="utf-8") as f_out:
        for cond in ("B", "C"):
            for fix in fixtures:
                for rep in range(n):
                    seed, run_id, code_rev = 5000 + rep * 41, f"run_{rep}", "rev_v2"
                    store = {"shared_art": [{"id": 1, "val": 100}], "other_art": [{"id": 2, "val": 200}], "art|with=eq->arrow": [{"id": 3, "val": 300}]}
                    if fix == "1_SIBLINGS_SAME_REF_BOTH_MATCH":
                        gt = [{"claim_id": "sib_1", "real_hash": sha256_data(store["shared_art"])}, {"claim_id": "sib_2", "real_hash": sha256_data(store["shared_art"])}]
                        items = [{"claim_id": "sib_1", "artifact_ref": "shared_art", "stage": "verified", "note": "ok"}, {"claim_id": "sib_2", "artifact_ref": "shared_art", "stage": "verified", "note": "ok"}]
                        expected_inv = set()
                    elif fix == "2_SIBLINGS_SAME_REF_ONE_MISMATCH":
                        gt = [{"claim_id": "sib_1", "real_hash": sha256_data(store["shared_art"])}, {"claim_id": "sib_2", "real_hash": sha256_data(store["other_art"])}]
                        items = [{"claim_id": "sib_1", "artifact_ref": "shared_art", "stage": "verified", "note": "ok"}, {"claim_id": "sib_2", "artifact_ref": "shared_art", "stage": "verified", "note": "wrong_target"}]
                        expected_inv = {"sib_2"}
                    elif fix == "3_ROLE_DRIFT_HYPOTHESIS_AS_VERIFIED":
                        gt = [{"claim_id": "c_hyp", "real_hash": sha256_data(store["shared_art"])}]
                        items = [{"claim_id": "c_hyp", "artifact_ref": "shared_art", "stage": "hypothesis", "note": "unverified_plan"}]
                        expected_inv = {"c_hyp"}
                    elif fix == "4_DUPLICATE_CLAIM_IDS":
                        gt = [{"claim_id": "c_dup", "real_hash": sha256_data(store["shared_art"])}]
                        items = [{"claim_id": "c_dup", "artifact_ref": "shared_art", "stage": "verified", "note": "first"}, {"claim_id": "c_dup", "artifact_ref": "other_art", "stage": "verified", "note": "shadow"}]
                        expected_inv = {"c_dup"}
                    elif fix == "5_UNEXPECTED_EXTRA_CLAIM":
                        gt = [{"claim_id": "c_legit", "real_hash": sha256_data(store["shared_art"])}]
                        items = [{"claim_id": "c_legit", "artifact_ref": "shared_art", "stage": "verified", "note": "ok"}, {"claim_id": "c_injected", "artifact_ref": "other_art", "stage": "verified", "note": "rogue"}]
                        expected_inv = {"c_legit"}
                    else:
                        gt = [{"claim_id": "c_inj", "real_hash": sha256_data(store["art|with=eq->arrow"])}]
                        items = [{"claim_id": "c_inj", "artifact_ref": "art|with=eq->arrow", "stage": "verified", "note": "special_chars"}]
                        expected_inv = set()
                    llm = llamar_llm_estricto(construir_prompt(cond, items, run_id, code_rev), seed)
                    ev = verificar_salida(cond, llm["response"], store, gt, code_rev, run_id)
                    exact = ev["invalidados"] == expected_inv
                    row = {"condition": cond, "fixture": fix, "rep": rep + 1, "llm_ok": llm["llm_ok"], "latency_ms": llm["latency_ms"], "eval_count": llm["eval_count"], "exact_match": exact, "format_error": ev["format_error"], "expected_invalid": sorted(expected_inv), "observed_invalid": sorted(ev["invalidados"]), "raw_output": llm["response"]}
                    f_out.write(json.dumps(row, ensure_ascii=False) + "\n")
                    resumen[cond][fix].append(row)
                    print(f"  [{cond}] {fix:37s} rep {rep+1}/{n} -> exact={exact} fmt_err={ev['format_error']} tok={llm['eval_count']}", flush=True)
    print("\n=== RESUMEN HOSTILE SUITE V2 (B=JSON vs C=HEKT-NOVA | Sin fallback | Con telemetria LLM) ===")
    print("| Fixture Hostil | B (JSON) Exact % | C (HEKT-NOVA) Exact % | B Fmt Err | C Fmt Err | B Tokens | C Tokens |")
    print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for fix in fixtures:
        b_rows, c_rows = resumen["B"][fix], resumen["C"][fix]
        print(f"| `{fix}` | {sum(1 for r in b_rows if r['exact_match'])/n*100:.0f}% | {sum(1 for r in c_rows if r['exact_match'])/n*100:.0f}% | {sum(1 for r in b_rows if r['format_error'])}/{n} | {sum(1 for r in c_rows if r['format_error'])}/{n} | {sum(r['eval_count'] for r in b_rows)/n:.1f} | {sum(r['eval_count'] for r in c_rows)/n:.1f} |")

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--n", type=int, default=5); a = p.parse_args(); correr_suite(a.n)
