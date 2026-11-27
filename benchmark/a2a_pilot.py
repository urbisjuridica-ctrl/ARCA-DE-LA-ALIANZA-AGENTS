from concurrent.futures import ThreadPoolExecutor
import json, os, re, tempfile, threading, time, urllib.request
from hekt_nova.a2a_server import HektA2AServer
from hekt_nova.a2a_bridge import wrap_hekt_a2a_part
from hekt_nova.agent_runtime import SignedAgentEmitter
from hekt_external_verifier import parse_hekt_header, is_action_allowed, verify_message

def est_tokens(obj) -> int:
    raw = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return max(1, round(len(raw) / 4))

def pct(values, p: float) -> float:
    s = sorted(values)
    idx = min(len(s) - 1, max(0, int(round((p / 100.0) * (len(s) - 1)))))
    return round(s[idx], 3)

def run_pilot():
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(db_fd)
    os.environ["HEKT_NONCE_DB"] = db_path
    client_k1 = SignedAgentEmitter(agent_name="client_a", key_id="client-a2a-k1", audience="a2a-prod")
    client_k2 = SignedAgentEmitter(agent_name="client_a_rot", key_id="client-a2a-k2", audience="a2a-prod")
    rogue = SignedAgentEmitter(agent_name="rogue_b", key_id="rogue-k9", audience="a2a-prod")
    trusted = {**client_k1.trusted_keys, **client_k2.trusted_keys}
    gateway = HektA2AServer(host="127.0.0.1", port=0, trusted_keys=trusted, expected_audience="a2a-prod")
    httpd = gateway.make_httpd()
    port = httpd.server_port
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    valid_claim = client_k1.emit_verified("AUD", "VERIFY_TRACE", {"artifact": "SKILL.md"}, body="sha_ok=1")
    tampered_body = valid_claim["message"].replace("sha_ok=1", "sha_ok=0")
    rogue_claim = rogue.emit_verified("AUD", "VERIFY_TRACE", {"artifact": "SKILL.md"}, body="sha_ok=1")
    expired_ts = str(int(time.time()) - 900)
    expired_hdr = re.sub(r"ts=[0-9]+", f"ts={expired_ts}", valid_claim["message"], count=1)

    scenarios = [
        ("1_valid_signed_task", valid_claim["message"], True),
        ("2_replay_same_nonce", valid_claim["message"], False),
        ("3_tampered_body_hash", tampered_body, False),
        ("4_untrusted_rogue_key", rogue_claim["message"], False),
        ("5_expired_timestamp_900s", expired_hdr, False),
    ]

    stats = {
        "A_plain_a2a": {"correct": 0, "lat_ms": [], "payload_tok": [], "envelope_tok": []},
        "B_hekt_syntax_only": {"correct": 0, "lat_ms": [], "payload_tok": [], "envelope_tok": []},
        "C_hekt_v304_fail_closed": {"correct": 0, "lat_ms": [], "payload_tok": [], "envelope_tok": []},
    }

    try:
        for name, hekt_msg, should_accept in scenarios:
            t0 = time.perf_counter()
            plain_req = {"jsonrpc": "2.0", "id": name, "method": "tasks/send", "params": {"id": name, "message": {"role": "agent", "parts": [{"kind": "text", "text": "Verify SKILL.md trace"}]}}}
            stats["A_plain_a2a"]["lat_ms"].append((time.perf_counter() - t0) * 1000)
            stats["A_plain_a2a"]["correct"] += int(True == should_accept)
            stats["A_plain_a2a"]["payload_tok"].append(est_tokens("Verify SKILL.md trace"))
            stats["A_plain_a2a"]["envelope_tok"].append(est_tokens(plain_req))

            t0 = time.perf_counter()
            parsed, err = parse_hekt_header(hekt_msg)
            ok_syn = (err is None and parsed is not None and is_action_allowed(parsed))
            stats["B_hekt_syntax_only"]["lat_ms"].append((time.perf_counter() - t0) * 1000)
            stats["B_hekt_syntax_only"]["correct"] += int(ok_syn == should_accept)
            stats["B_hekt_syntax_only"]["payload_tok"].append(est_tokens(hekt_msg))
            stats["B_hekt_syntax_only"]["envelope_tok"].append(est_tokens({"jsonrpc": "2.0", "id": name, "method": "tasks/send", "params": {"id": name, "message": wrap_hekt_a2a_part(hekt_msg)}}))

            rpc_req = {"jsonrpc": "2.0", "id": name, "method": "tasks/send", "params": {"id": name, "message": wrap_hekt_a2a_part(hekt_msg)}}
            t0 = time.perf_counter()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/a2a", data=json.dumps(rpc_req).encode(), headers={"Content-Type": "application/json"}, method="POST")
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
            lat = (time.perf_counter() - t0) * 1000
            accepted = "result" in resp
            stats["C_hekt_v304_fail_closed"]["lat_ms"].append(lat)
            stats["C_hekt_v304_fail_closed"]["correct"] += int(accepted == should_accept)
            stats["C_hekt_v304_fail_closed"]["payload_tok"].append(est_tokens(hekt_msg))
            stats["C_hekt_v304_fail_closed"]["envelope_tok"].append(est_tokens(rpc_req))

        # Carga concurrente N=100 legítima (50 con k1 + 50 con k2 tras rotación de clave)
        legit_claims = [
            (client_k1 if i < 50 else client_k2).emit_verified("AUD", "VERIFY_TRACE", {"seq": str(i)}, body=f"item={i}")
            for i in range(100)
        ]
        pure_crypto_ms = []
        seen_mem = set()
        for c in legit_claims:
            t0 = time.perf_counter()
            r_mem = verify_message(c["message"], trusted_keys=trusted, expected_audience="a2a-prod", seen_nonces=seen_mem)
            pure_crypto_ms.append((time.perf_counter() - t0) * 1000)
            assert r_mem.status == "VALID"

        def send_legit(idx_claim):
            idx, c = idx_claim
            rpc_req = {"jsonrpc": "2.0", "id": f"legit-{idx}", "method": "tasks/send", "params": {"id": f"legit-{idx}", "message": wrap_hekt_a2a_part(c["message"])}}
            t0 = time.perf_counter()
            req = urllib.request.Request(f"http://127.0.0.1:{port}/a2a", data=json.dumps(rpc_req).encode(), headers={"Content-Type": "application/json"}, method="POST")
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            return ("result" in resp), (time.perf_counter() - t0) * 1000

        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(send_legit, enumerate(legit_claims)))

        legit_ok = sum(1 for ok, _ in results if ok)
        http_lats = [lat for _, lat in results]
    finally:
        httpd.shutdown()
        for ext in ("", "-wal", "-shm"):
            if os.path.exists(db_path + ext):
                os.remove(db_path + ext)

    summary = {"adversarial_5_scenarios": {}}
    for k, v in stats.items():
        n = len(scenarios)
        summary["adversarial_5_scenarios"][k] = {
            "security_accuracy": f"{v['correct']}/{n} ({round(100*v['correct']/n, 1)}%)",
            "avg_latency_ms": round(sum(v["lat_ms"]) / n, 3),
            "avg_payload_tokens": round(sum(v["payload_tok"]) / n, 1),
            "avg_a2a_envelope_tokens": round(sum(v["envelope_tok"]) / n, 1),
        }
    summary["concurrent_legit_stress_N100"] = {
        "accepted": f"{legit_ok}/100",
        "false_positive_rate": f"{round(100 * (100 - legit_ok) / 100, 1)}%",
        "pure_ed25519_verify_ms": {"p50": pct(pure_crypto_ms, 50), "p95": pct(pure_crypto_ms, 95), "p99": pct(pure_crypto_ms, 99)},
        "end_to_end_http_sqlite_wal_ms": {"p50": pct(http_lats, 50), "p95": pct(http_lats, 95), "p99": pct(http_lats, 99)},
    }
    open("benchmark/a2a_pilot_results.json", "w", encoding="utf-8").write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    run_pilot()
