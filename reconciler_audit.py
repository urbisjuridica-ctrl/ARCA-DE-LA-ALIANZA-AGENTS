import urllib.parse
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
    """Extrae dominios [H::<DOM>], pares key=val (1 linea o multilinea) y accion emit=<ACTION>."""
    if not header or not header.strip():
        return {"domains": [], "fields": {}, "emit": None}
    dominios = []
    kv = {}
    emit_val = None
    for raw_line in header.strip().splitlines():
        linea = raw_line.strip()
        if not linea:
            continue
        for d in re.findall(r"\[H::([A-Z]{3})\]", linea):
            if d not in dominios:
                dominios.append(d)
        em = re.search(r"(?:->|→)\s*emit=([A-Za-z0-9_\-]+)", linea)
        if em:
            emit_val = em.group(1)
        sin_doms = re.sub(r"\[H::[A-Z]{3}\]", "", linea)
        sin_emit = re.sub(r"(?:->|→)\s*emit=[A-Za-z0-9_\-]+", "", sin_doms)
        for seg in sin_emit.split("|"):
            if "=" in seg:
                k, v = seg.split("=", 1)
                kv[k.strip()] = urllib.parse.unquote(v.strip().strip('"'))
    return {"domains": dominios, "fields": kv, "emit": emit_val}

def _last_record_hash(ledger_path: str) -> str:
    if not os.path.exists(ledger_path):
        return "0" * 64
    last_line = ""
    with open(ledger_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last_line = line.strip()
    return json.loads(last_line).get("record_hash", "0" * 64) if last_line else "0" * 64

def reconcile_claim_and_check(claim_header: str, external_trace: dict | None, ledger_path: str = LEDGER_FILE) -> dict:
    """
    Compara Claim (header HEKT-NOVA) vs Check (traza externa fuera de control del LLM):
      - Todo coincide                      -> MATCH
      - Diferencia en enlace/accion/policy -> MISMATCH
      - Traza existe pero Claim ausente    -> MISMATCH (undeclared_action)
      - Claim existe pero Check ausente    -> INCONCLUSIVE (missing_witness)
    """
    parsed = parse_claim_header(claim_header or "")
    has_claim = bool(parsed["domains"] or parsed["fields"])
    has_check = bool(external_trace)

    claim_hash = _canonical_sha256({"raw_header": (claim_header or "").strip(), "parsed": parsed}) if has_claim else "none"
    check_hash = _canonical_sha256(external_trace) if has_check else "none"

    mismatch_fields = []
    reasons = []

    if has_check and not has_claim:
        verdict = "MISMATCH"
        mismatch_fields.append("claim_header")
        reasons.append("Traza ejecutada sin declaracion previa (Claim ausente)")
    elif has_claim and not has_check:
        verdict = "INCONCLUSIVE"
        mismatch_fields.append("external_trace")
        reasons.append("Claim declarado sin testigo externo (Check ausente)")
    elif not has_claim and not has_check:
        verdict = "INCONCLUSIVE"
        reasons.append("Sin Claim ni Check")
    else:
        f = parsed["fields"]
        t = external_trace

        # 1. Enlace (audit_ref / trace_id y agent_id)
        c_ref = f.get("audit_ref") or f.get("trace_id")
        o_ref = t.get("trace_id") or t.get("audit_ref")
        if c_ref and o_ref and c_ref != o_ref:
            mismatch_fields.append("audit_ref")
            reasons.append(f"audit_ref ({c_ref}) != trace_id ({o_ref})")

        if f.get("agent_id") and t.get("agent_id") and f["agent_id"] != t["agent_id"]:
            mismatch_fields.append("agent_id")
            reasons.append(f"agent_id ({f['agent_id']}) != ({t['agent_id']})")

        # 2. Accion, herramienta y objetivo
        c_act = f.get("declared_action") or parsed["emit"]
        o_act = t.get("observed_action")
        if c_act and o_act and c_act != o_act:
            mismatch_fields.append("declared_action")
            reasons.append(f"declared_action ({c_act}) != observed_action ({o_act})")

        if f.get("tool") and t.get("tool") and f["tool"] != t["tool"]:
            mismatch_fields.append("tool")
            reasons.append(f"tool ({f['tool']}) != ({t['tool']})")

        if f.get("target") and t.get("target") and f["target"] != t["target"]:
            mismatch_fields.append("target")
            reasons.append(f"target ({f['target']}) != ({t['target']})")

        # 3. Restricciones de politica (constraint=read_only)
        if f.get("constraint") == "read_only":
            op_mode = (t.get("operation_type") or t.get("tool") or "").lower()
            if any(w in op_mode for w in ("write", "delete", "remove", "rm", "update", "patch", "post", "exec")):
                mismatch_fields.append("constraint")
                reasons.append(f"Violacion de constraint=read_only con operacion ({op_mode})")

        # 4. Regla de inmutabilidad de provenance (NO_MUTABLE_ALIASES)
        doms = set(parsed["domains"])
        if doms & {"DBX", "MEM", "VER", "AUD"}:
            mutable_words = {"cleaned", "latest", "current", "default", "head"}
            has_digest = bool(f.get("artifact_hash") or f.get("dataset_hash"))
            has_rev = bool(f.get("code_rev") or f.get("version"))
            for k_field, v_field in f.items():
                if v_field.lower() in mutable_words and (not has_digest or not has_rev):
                    mismatch_fields.append(k_field)
                    reasons.append(f"Alias mutable ({k_field}={v_field}) sin artifact_hash/dataset_hash y code_rev")

        verdict = "MISMATCH" if mismatch_fields else "MATCH"

    emit_audit = "AUDIT_ALERT" if verdict == "MISMATCH" else "AUDIT_REPORT"
    mf_str = ",".join(mismatch_fields) if mismatch_fields else "none"
    run_id = parsed["fields"].get("run_id", "none")
    audit_header = (
        f"[H::AUD] result={verdict} | run_id={run_id} | mismatch_fields={mf_str} | "
        f"claim_hash=sha256:{claim_hash[:12]} | trace_hash=sha256:{check_hash[:12]} -> emit={emit_audit}"
    )

    prev_hash = _last_record_hash(ledger_path)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "mismatch_fields": mismatch_fields,
        "reasons": reasons,
        "audit_header": audit_header,
        "claim": parsed,
        "claim_hash": claim_hash,
        "check_hash": check_hash,
        "prev_hash": prev_hash
    }
    record["record_hash"] = _canonical_sha256(record)

    with open(ledger_path, "a", encoding="utf-8") as f_out:
        f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record

if __name__ == "__main__":
    claim_ok = """[H::AGT] agent_id=evangelista_v1 | version=2.3.2 | run_id=run_7f3a9c2e
[H::AUD] audit_ref=trace_9b2e1d | witness_required=true
[H::VER] declared_action=tool_call | tool=read_file | target=/data/contracts/2026-Q3.pdf
[H::ETH] policy=no_exfiltrate | constraint=read_only"""

    r_match = reconcile_claim_and_check(claim_ok, {
        "trace_id": "trace_9b2e1d", "agent_id": "evangelista_v1",
        "observed_action": "tool_call", "tool": "read_file",
        "target": "/data/contracts/2026-Q3.pdf", "operation_type": "read"
    })
    r_mismatch = reconcile_claim_and_check(claim_ok, {
        "trace_id": "trace_9b2e1d", "agent_id": "evangelista_v1",
        "observed_action": "tool_call", "tool": "write_file",
        "target": "/data/secrets/keys.env", "operation_type": "write"
    })
    r_undeclared = reconcile_claim_and_check("", {
        "trace_id": "trace_9b2e99", "agent_id": "evangelista_v1",
        "observed_action": "tool_call", "tool": "delete_file"
    })
    r_inconc = reconcile_claim_and_check(claim_ok, None)

    for r in (r_match, r_mismatch, r_undeclared, r_inconc):
        print(r["audit_header"])
