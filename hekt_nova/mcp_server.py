import json, sys
from hekt_external_verifier import verify_message, sha256_canonical_json

def handle_rpc(req: dict) -> dict:
    method = req.get("method", "")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05", "serverInfo": {"name": "hekt-nova-verifier", "version": "2.4.0"}, "capabilities": {"tools": {}}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": [
            {"name": "verify_hekt_claim", "description": "Verifica deterministamente una cabecera HEKT-NOVA v2.4 (VALID/REJECTED/UNVERIFIED) y registra testigo SHA-256.", "inputSchema": {"type": "object", "properties": {"header": {"type": "string"}, "artifact_path": {"type": "string"}}, "required": ["header"]}},
            {"name": "canonical_sha256", "description": "Calcula el digest SHA-256 canónico (NFC/LF/RFC8785) de un objeto JSON.", "inputSchema": {"type": "object", "properties": {"payload": {"type": "object"}}, "required": ["payload"]}},
        ]}}
    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        if name == "verify_hekt_claim":
            path = args.get("artifact_path")
            raw = open(path, "rb").read() if path else None
            res = verify_message(args["header"], canonical_bytes=raw)
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": json.dumps(res.__dict__, ensure_ascii=False)}]}}
        if name == "canonical_sha256":
            digest = sha256_canonical_json(args["payload"])
            return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": digest}]}}
    return {"jsonrpc": "2.0", "id": rid, "result": {}}

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        resp = handle_rpc(json.loads(line))
        if resp.get("id") is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
