import hashlib, json, os, re, urllib.parse
from datetime import datetime, timezone

LEDGER_FILE = "witness_ledger.jsonl"

def _sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def parse_hekt_claim(header_line: str) -> dict:
    domains = re.findall(r"\[H::([A-Z]{3})\]", header_line)
    pre_arrow, _, post_arrow = header_line.partition("->")
    emit_match = re.search(r"emit=([A-Z0-9_]+)", post_arrow)
    emit_action = emit_match.group(1) if emit_match else None
    clean_kv = re.sub(r"\[H::[A-Z]{3}\]", "", pre_arrow)
    fields = {}
    for seg in clean_kv.split("|"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            fields[k.strip()] = urllib.parse.unquote(v.strip().strip('"'))
    return {"domains": domains, "fields": fields, "emit": emit_action}

def _append_witness_row(record: dict) -> str:
    prev_hash = "0" * 64
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "rb") as f:
            lines = f.read().splitlines()
            if lines:
                prev_hash = hashlib.sha256(lines[-1]).hexdigest()
    record["prev_hash"] = prev_hash
    raw = json.dumps(record, sort_keys=True, ensure_ascii=False).encode("utf-8")
    record["row_hash"] = hashlib.sha256(raw).hexdigest()
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record["row_hash"]

def verify_external_execution(hekt_claim_header: str, target_filepath: str, observed_action: str, expected_sha256: str | None = None, active_head_rev: str | None = None) -> dict:
    claim = parse_hekt_claim(hekt_claim_header)
    fields = claim["fields"]
    mismatches = []
    mutable_aliases = {"latest", "cleaned", "current", "default", "head"}
    for k, v in fields.items():
        if v.lower() in mutable_aliases and "artifact_hash" not in fields:
            mismatches.append(f"MUTABLE_ALIAS_REJECTED:{k}={v}")
    if not os.path.exists(target_filepath):
        real_hash = None
        mismatches.append(f"ARTIFACT_NOT_FOUND:{target_filepath}")
    else:
        with open(target_filepath, "rb") as f:
            real_hash = _sha256_bytes(f.read())
        if expected_sha256 and real_hash != expected_sha256:
            mismatches.append(f"HASH_MISMATCH:claimed={expected_sha256},real={real_hash}")
        if "artifact_hash" in fields and fields["artifact_hash"] != real_hash:
            mismatches.append(f"HEADER_HASH_MISMATCH:claimed={fields['artifact_hash']},real={real_hash}")
    if active_head_rev and fields.get("code_rev") and fields["code_rev"] != active_head_rev:
        mismatches.append(f"SUPERSEDED_REV:claimed={fields['code_rev']},head={active_head_rev}")
    if claim["emit"] != observed_action:
        mismatches.append(f"ACTION_MISMATCH:emit={claim['emit']},observed={observed_action}")
    verdict = "MISMATCH" if mismatches else "MATCH"
    witness_header = f"[H::{'ERR' if mismatches else 'AUD'}] [H::VER] verdict={verdict} | real_hash={real_hash or 'NONE'} -> emit={'HALT_AND_LOG' if mismatches else 'COMMIT_WITNESS'}"
    witness_record = {"timestamp": datetime.now(timezone.utc).isoformat(), "verdict": verdict, "claim_header": hekt_claim_header, "witness_header": witness_header, "real_hash": real_hash, "observed_action": observed_action, "mismatches": mismatches}
    witness_record["row_hash"] = _append_witness_row(witness_record)
    return witness_record

if __name__ == "__main__":
    r_ok = verify_external_execution("[H::VER] [H::AUD] claim_id=test_ok | code_rev=v2.3.3 -> emit=AUDIT_FILE", "SKILL.md", "AUDIT_FILE", active_head_rev="v2.3.3")
    r_bad = verify_external_execution("[H::VER] [H::DBX] dataset=latest -> emit=TRAIN", "SKILL.md", "READ_ONLY", active_head_rev="v2.3.3")
    print("TEST 1 (MATCH):", r_ok["verdict"], r_ok["witness_header"])
    print("TEST 2 (MISMATCH):", r_bad["verdict"], r_bad["mismatches"])
