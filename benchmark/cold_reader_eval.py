import json, os, re, time, urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
MODELO = "llama3.2"

ITEMS_20 = [
    ("WORLD_CLAIM", '{"obs":"invoice_total_is_80","src":"agent_a"}', '[H::EPI] claim=invoice_total_80 | src=agent_a -> emit=ASSERT'),
    ("AUDIT_VERDICT", '{"sha":"9f8a2b","status":"MISMATCH","by":"reconciler"}', '[H::AUD] hash=9f8a2b | verdict=MISMATCH -> emit=HALT_AND_LOG'),
    ("DIRECTIVE", '{"policy":"read_only","scope":"prod_db"}', '[H::ETH] constraint=read_only | scope=prod_db -> emit=ENFORCE'),
    ("WORLD_CLAIM", '{"note":"source_csv_has_120_rows","step":"extract"}', '[H::EPI] rows=120 | step=extract -> emit=REPORT'),
    ("AUDIT_VERDICT", '{"check":"artifact_v2","ok":true,"witness":"row_44"}', '[H::AUD] artifact=v2 | verdict=MATCH -> emit=COMMIT_WITNESS'),
    ("DIRECTIVE", '{"action":"reject_mutable_alias","target":"latest"}', '[H::ETH] rule=NO_MUTABLE_ALIAS | target=latest -> emit=BLOCK'),
    ("WORLD_CLAIM", '{"estimate":"latency_dropped_30pct","run":"r9"}', '[H::EPI] metric=latency_minus_30pct | run=r9 -> emit=HYPOTHESIZE'),
    ("AUDIT_VERDICT", '{"rev":"v1","head":"v2","flag":"SUPERSEDED"}', '[H::AUD] rev=v1 | head=v2 | verdict=SUPERSEDED -> emit=REJECT'),
    ("DIRECTIVE", '{"limit":"max_1_reply_per_thread","mode":"strict"}', '[H::ETH] limit=1_reply_per_thread | mode=strict -> emit=GUARD'),
    ("WORLD_CLAIM", '{"summary":"payee_matches_vendor_list","conf":0.82}', '[H::EPI] payee=vendor_ok | conf=0.82 -> emit=PROPOSE'),
    ("AUDIT_VERDICT", '{"digest_expected":"a1b2","digest_real":"c3d4"}', '[H::AUD] expected=a1b2 | real=c3d4 | verdict=DRIFT -> emit=FORK'),
    ("DIRECTIVE", '{"require":"external_sha256_before_pay"}', '[H::ETH] req=external_sha256 | gate=payment -> emit=REQUIRE'),
    ("WORLD_CLAIM", '{"finding":"three_duplicate_rows_in_batch"}', '[H::EPI] duplicates=3 | batch=current -> emit=FLAG'),
    ("AUDIT_VERDICT", '{"ledger_chain":"valid","verified_rows":18}', '[H::AUD] chain=valid | rows=18 | verdict=VERIFIED -> emit=SEAL'),
    ("DIRECTIVE", '{"forbid":"self_signed_execution_logs"}', '[H::ETH] forbid=self_attestation -> emit=PROHIBIT'),
    ("WORLD_CLAIM", '{"belief":"context_compaction_dropped_id"}', '[H::EPI] cause=compaction_loss -> emit=INFER'),
    ("AUDIT_VERDICT", '{"payload_bytes":4096,"witness_sig":"ed25519_ok"}', '[H::AUD] bytes=4096 | sig=ok | verdict=ATTESTED -> emit=LOG'),
    ("DIRECTIVE", '{"halt_if":"amount_delta_gt_zero"}', '[H::ETH] trigger=amount_delta_gt_0 -> emit=ABORT'),
    ("WORLD_CLAIM", '{"hypothesis":"user_prefers_concise_summary"}', '[H::EPI] user_pref=concise -> emit=ASSUME'),
    ("AUDIT_VERDICT", '{"evicted_claim":"c_stale_9","reason":"expired_ttl"}', '[H::AUD] evicted=c_stale_9 | reason=expired_ttl -> emit=EVICT'),
]

def clasificar_item(texto: str, seed: int) -> tuple[str, float, int]:
    t0 = time.perf_counter()
    prompt = (
        "You have NO prior schema documentation. Classify this single line into EXACTLY ONE label:\n"
        "- WORLD_CLAIM (an agent's observation, belief, or hypothesis about the world)\n"
        "- AUDIT_VERDICT (an external verification result, hash check, or ledger verdict)\n"
        "- DIRECTIVE (a policy rule, constraint, or operational instruction)\n\n"
        f"Line: {texto}\nReply with ONLY the label (WORLD_CLAIM, AUDIT_VERDICT, or DIRECTIVE)."
    )
    payload = json.dumps({"model": MODELO, "prompt": prompt, "stream": False, "options": {"temperature": 0.0, "seed": seed, "num_predict": 12}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode())
    out = data.get("response", "").strip().upper()
    label = "UNKNOWN"
    for cand in ("WORLD_CLAIM", "AUDIT_VERDICT", "DIRECTIVE"):
        if cand in out:
            label = cand
            break
    return label, (time.perf_counter() - t0) * 1000, len(texto) // 4

def correr_cold_reader(reps: int = 3):
    out_path = os.path.join(os.path.dirname(__file__), "cold_reader_per_run.jsonl")
    stats = {"B": {"ok": 0, "tot": 0, "ms": 0.0, "tok": 0}, "C": {"ok": 0, "tot": 0, "ms": 0.0, "tok": 0}}
    with open(out_path, "w", encoding="utf-8") as f:
        for cond, idx in (("B", 1), ("C", 2)):
            for r in range(reps):
                for i, item in enumerate(ITEMS_20):
                    gold, line = item.__getitem__(0), item.__getitem__(idx)
                    pred, ms, tok = clasificar_item(line, 7000 + r * 100 + i)
                    hit = pred == gold
                    stats[cond]["ok"] += int(hit)
                    stats[cond]["tot"] += 1
                    stats[cond]["ms"] += ms
                    stats[cond]["tok"] += tok
                    f.write(json.dumps({"cond": cond, "rep": r + 1, "item": i + 1, "gold": gold, "pred": pred, "hit": hit, "ms": round(ms, 1)}) + "\n")
                print(f"  [{cond}] Repetición {r+1}/{reps} -> Acierto acumulado: {stats[cond]['ok']}/{stats[cond]['tot']}", flush=True)

    print("\n=== RESULTADOS BENCHMARK COLD-READER (Sin esquema previo | 20 ítems x 3 reps = 60 por condición) ===")
    print("| Condición | Precisión Cold-Reader | Latencia Media / Ítem | Tokens Entrada / Ítem |")
    print("| :--- | :---: | :---: | :---: |")
    for cond, nom in (("B", "B (Raw JSON sin esquema)"), ("C", "C (HEKT-NOVA v2.3.3 sin esquema)")):
        s = stats[cond]
        print(f"| **{nom}** | {s['ok']/s['tot']*100:.1f}% ({s['ok']}/{s['tot']}) | {s['ms']/s['tot']:.1f} ms | {s['tok']/s['tot']:.1f} tok |")

if __name__ == "__main__":
    correr_cold_reader(3)
