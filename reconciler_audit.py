import hashlib
import json
import os
import re
from datetime import datetime, timezone

LEDGER_FILE = "witness_ledger.jsonl"

def _canonical_sha256(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def parse_claim_header(header: str) -> dict:
    """Extrae dominios [H::<DOM>], pares key=val y accion emit=<ACTION> de una cabecera HEKT-NOVA."""
    linea = header.strip().splitlines()[0] if header.strip() else ""
    dominios = re.findall(r"\[H::([A-Z]{3})\]", linea)
    emit_match = re.search(r"->\s*emit=([A-Za-z0-9_\-]+)", linea)
    sin_doms = re.sub(r"\[H::[A-Z]{3}\]", "", linea)
    sin_emit = re.sub(r"->\s*emit=[A-Za-z0-9_\-]+", "", sin_doms)
    kv = {}
    for segmento in sin_emit.split("|"):
        if "=" in segmento:
            k, v = segmento.split("=", 1)
            kv[k.strip()] = v.strip()
    return {
        "domains": dominios,
        "fields": kv,
        "emit": emit_match.group(1) if emit_match else None
    }

def _last_record_hash(ledger_path: str) -> str:
    if not os.path.exists(ledger_path):
        return "0" * 64
    last_line = ""
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line.strip()
    if not last_line:
        return "0" * 64
    return json.loads(last_line).get("record_hash", "0" * 64)

def reconcile_claim_and_check(claim_header: str, external_trace: dict, ledger_path: str = LEDGER_FILE) -> dict:
    """
    Compara la declaracion del agente (Claim) contra la traza externa fuera de su control (Check)
    y registra el veredicto en un ledger append-only encadenado por SHA-256.
    """
    parsed = parse_claim_header(claim_header)
    claim_hash = _canonical_sha256({"raw_header": claim_header.strip(), "parsed": parsed})
    check_hash = _canonical_sha256(external_trace)

    reasons = []
    if not parsed["domains"] or not external_trace:
        verdict = "INCONCLUSIVE"
        reasons.append("Falta cabecera valida o traza externa vacia")
    else:
        claimed_action = parsed["emit"]
        observed_action = external_trace.get("observed_action")
        if claimed_action and observed_action and claimed_action != observed_action:
            reasons.append(f"Accion declarada ({claimed_action}) != observada ({observed_action})")

        claimed_trace = parsed["fields"].get("trace_id")
        observed_trace = external_trace.get("trace_id")
        if claimed_trace and observed_trace and claimed_trace != observed_trace:
            reasons.append(f"trace_id declarado ({claimed_trace}) != observado ({observed_trace})")

        expected_hash = parsed["fields"].get("expected_hash")
        observed_output_hash = external_trace.get("output_hash")
        if expected_hash and observed_output_hash and expected_hash != observed_output_hash:
            reasons.append("expected_hash no coincide con output_hash real")

        verdict = "MISMATCH" if reasons else "MATCH"

    prev_hash = _last_record_hash(ledger_path)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "reasons": reasons,
        "claim": parsed,
        "claim_hash": claim_hash,
        "check_hash": check_hash,
        "prev_hash": prev_hash
    }
    record["record_hash"] = _canonical_sha256(record)

    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record

if __name__ == "__main__":
    r1 = reconcile_claim_and_check(
        "[H::AGT] [H::AUD] [H::VER] run_id=ev-01 | trace_id=tr-100 -> emit=POST_COMMENT",
        {"trace_id": "tr-100", "observed_action": "POST_COMMENT", "status": 201}
    )
    r2 = reconcile_claim_and_check(
        "[H::AGT] [H::AUD] [H::VER] run_id=ev-01 | trace_id=tr-101 -> emit=READ_ONLY",
        {"trace_id": "tr-101", "observed_action": "DELETE_RECORD", "status": 200}
    )
    print("TEST 1:", r1["verdict"], "| hash:", r1["record_hash"][:16])
    print("TEST 2:", r2["verdict"], "| motivos:", r2["reasons"], "| prev_hash==r1:", r2["prev_hash"] == r1["record_hash"])
