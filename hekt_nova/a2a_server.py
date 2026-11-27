import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from hekt_nova.a2a_bridge import build_a2a_agent_card, wrap_hekt_a2a_part, verify_a2a_message
from hekt_nova.agent_runtime import SignedAgentEmitter

class HektA2AServer:
    """Servidor HTTP A2A ligero con verificación fail-closed HEKT-NOVA v3.0.4 y respuesta firmada."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8099, emitter: Optional[SignedAgentEmitter] = None, trusted_keys: Optional[Dict[str, str]] = None, expected_audience: str = "a2a-prod"):
        self.host = host
        self.port = port
        self.emitter = emitter or SignedAgentEmitter(agent_name="arca_a2a_gateway", key_id="arca-a2a-srv-k1", audience=expected_audience)
        self.trusted_keys: Dict[str, str] = dict(self.emitter.trusted_keys)
        if trusted_keys:
            self.trusted_keys.update(trusted_keys)
        self.expected_audience = expected_audience
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.card = build_a2a_agent_card(
            name="ARCA-HEKT-NOVA-A2A-Gateway",
            description="A2A Agent endpoint protected by HEKT-NOVA v3.0.4 Ed25519 + SQLite WAL verification",
            url=f"http://{host}:{port}/a2a",
            skills=[{"id": "hekt-audit-verify", "name": "Verify & Attest HEKT-NOVA Task"}],
        )

    def handle_rpc(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}
        if method == "tasks/get":
            tid = str(params.get("id", ""))
            if tid not in self.tasks:
                return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32002, "message": "Task not found"}}
            return {"jsonrpc": "2.0", "id": req_id, "result": self.tasks[tid]}
        if method != "tasks/send":
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
        task_id = str(params.get("id", "unknown-task"))
        msg = params.get("message") or {}
        res = verify_a2a_message(msg, trusted_keys=self.trusted_keys, expected_audience=self.expected_audience)
        if res.status != "VALID":
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32001, "message": f"HEKT_REJECTED:{res.reason}"}}
        attest = self.emitter.emit_verified(
            "AUD",
            "ATTEST_ARTIFACT",
            {"task_id": str(task_id), "client_action": str(res.action or "NONE")},
            body=f"task={task_id} verified_reason={res.reason} row_hash={res.row_hash}",
        )
        reply_msg = wrap_hekt_a2a_part(attest["message"], human_summary=f"Task {task_id} verified ({res.reason}).")
        task_obj = {
            "id": task_id,
            "status": {"state": "completed"},
            "artifacts": [{"name": "hekt-attestation", "parts": reply_msg["parts"]}],
        }
        self.tasks[task_id] = task_obj
        return {"jsonrpc": "2.0", "id": req_id, "result": task_obj}

    def make_httpd(self) -> ThreadingHTTPServer:
        gateway = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _send_json(self, code: int, obj: Dict[str, Any]) -> None:
                raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                if self.path == "/.well-known/agent.json":
                    self._send_json(200, gateway.card)
                else:
                    self._send_json(404, {"error": "Not Found"})

            def do_POST(self) -> None:
                if self.path != "/a2a":
                    self._send_json(404, {"error": "Not Found"})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                try:
                    data = json.loads(self.rfile.read(length).decode("utf-8"))
                except Exception:
                    self._send_json(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
                    return
                self._send_json(200, gateway.handle_rpc(data))

        return ThreadingHTTPServer((self.host, self.port), Handler)

if __name__ == "__main__":
    srv = HektA2AServer()
    httpd = srv.make_httpd()
    print(f"HEKT-NOVA A2A Server listening on http://{srv.host}:{srv.port} (/.well-known/agent.json & /a2a)")
    httpd.serve_forever()
