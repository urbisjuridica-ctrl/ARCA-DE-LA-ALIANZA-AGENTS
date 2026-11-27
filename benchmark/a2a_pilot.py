import re
import json, os, tempfile, threading, time, urllib.request
from hekt_nova.a2a_server import HektA2AServer
from hekt_nova.a2a_bridge import wrap_hekt_a2a_part, HEKT_A2A_MIME
from hekt_nova.agent_runtime import SignedAgentEmitter
from hekt_external_verifier import parse_hekt_header, is_action_allowed

def est_tokens(obj) -> int:
    raw = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    return max(1, round(len(raw) / 4))

def run_pilot():
    db_fd, db_path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(db_fd)
    os.environ["HEKT_NONCE_DB"] = db_path
    client = SignedAgentEmitter(agent_name="client_a", key_id="client-a2a-k1", audience="a2a-prod")
    rogue = SignedAgentEmitter(agent_name="rogue_b", key_id="rogue-k9", audience="a2a-prod")
    gateway = HektA2AServer(host="127.0.0.1", port=0, trusted_keys=client.trusted_keys, expected_audience="a2a-prod")
    httpd = gateway.make_httpd()
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    valid_claim = client.emit_verified("AUD", "VERIFY_TRACE", {"artifact": "SKILL.md"}, body="sha_ok=1")
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
            # Condición A: A2A sin verificador externo (acepta todo transporte válido)
            t0 = time.perf_counter()
            plain_req = {"jsonrpc": "2.0", "id": name, "method": "tasks/send", "params": {"id": name, "message": {"role": "agent", "parts": [{"kind": "text", "text": "Verify SKILL.md trace"}]}}}
            stats["A_plain_a2a"]["lat_ms"].append((time.perf_counter() - t0) * 1000)
            stats["A_plain_a2a"]["correct"] += int(True == should_accept)
            stats["A_plain_a2a"]["payload_tok"].append(est_tokens("Verify SKILL.md trace"))
            stats["A_plain_a2a"]["envelope_tok"].append(est_tokens(plain_req))

            # Condición B: Solo sintaxis HEKT (sin crypto/nonce/sha256)
            t0 = time.perf_counter()
            parsed, err = parse_hekt_header(hekt_msg)
            ok_syn = (err is None and parsed is not None and is_action_allowed(parsed)[0])
            stats["B_hekt_syntax_only"]["lat_ms"].append((time.perf_counter() - t0) * 1000)
            stats["B_hekt_syntax_only"]["correct"] += int(ok_syn == should_accept)
            stats["B_hekt_syntax_only"]["payload_tok"].append(est_tokens(hekt_msg))
            stats["B_hekt_syntax_only"]["envelope_tok"].append(est_tokens({"jsonrpc": "2.0", "id": name, "method": "tasks/send", "params": {"id": name, "message": wrap_hekt_a2a_part(hekt_msg)}}))

            # Condición C: A2A + HEKT-NOVA v3.0.4 HTTP real (fail-closed)
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

        # Verificar también tasks/get sobre la tarea válida
        get_req = {"jsonrpc": "2.0", "id": "get-1", "method": "tasks/get", "params": {"id": "1_valid_signed_task"}}
        get_resp = json.loads(urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{port}/a2a", data=json.dumps(get_req).encode(), headers={"Content-Type": "application/json"}, method="POST"), timeout=5).read().decode())
        assert get_resp["result"]["status"]["state"] == "completed"
    finally:
        httpd.shutdown()
        for ext in ("", "-wal", "-shm"):
            if os.path.exists(db_path + ext):
                os.remove(db_path + ext)

    summary = {}
    for k, v in stats.items():
        n = len(scenarios)
        summary[k] = {
            "security_accuracy": f"{v['correct']}/{n} ({round(100*v['correct']/n, 1)}%)",
            "avg_latency_ms": round(sum(v["lat_ms"]) / n, 3),
            "avg_payload_tokens": round(sum(v["payload_tok"]) / n, 1),
            "avg_a2a_envelope_tokens": round(sum(v["envelope_tok"]) / n, 1),
        }
    open("benchmark/a2a_pilot_results.json", "w", encoding="utf-8").write(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    run_pilot()
