from dataclasses import dataclass
import hashlib, hmac, json, os, re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

LEDGER_FILE = "witness_ledger.jsonl"
ALLOWED_DOMAINS: Set[str] = {"AGT", "VER", "AUD", "ETH", "ERR", "DOC", "HER", "EPI"}
MUTABLE_ALIASES: Set[str] = {"latest", "cleaned", "current", "default", "head"}

DOMAIN_ACTION_MATRIX: Dict[str, Set[str]] = {
    "AGT": {"REGISTER_PRESENCE", "TEACH_SYNTAX", "INTRO"},
    "VER": {"CLAIM_CHECK", "ASSERT_FACT", "AUDIT_FILE", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "AUD": {"VERIFY_TRACE", "ATTEST_ARTIFACT", "COMMIT_WITNESS", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "ETH": {"ENFORCE_POLICY", "DECLARE_CONSTRAINT"},
    "ERR": {"FORK_MISMATCH", "REPORT_ERROR", "HALT_AND_LOG"},
    "DOC": {"TEACH_SYNTAX", "INDEX_REPO"},
    "HER": {"OPEN_DIALOGUE", "ACKNOWLEDGE_CRITIQUE"},
    "EPI": {"ASSERT", "HYPOTHESIZE", "REPORT"},
}

HEADER_RE = re.compile(r"^((?:\[H::[A-Z]{3}\]\s*)+)\s+(.+?)\s+->\s+emit=([A-Z0-9_]+)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

@dataclass
class ParsedHeader:
    domains: List[str]
    fields: Dict[str, str]
    action: str

@dataclass
class VerificationResult:
    status: str  # "VALID" | "REJECTED" | "UNVERIFIED"
    reason: str
    domains: Optional[List[str]] = None
    action: Optional[str] = None
    computed_sha256: Optional[str] = None
    row_hash: Optional[str] = None

def unescape_hekt_value(raw_val: str) -> str:
    return raw_val.replace("%7C", "|").replace("%3D", "=").replace("%3E", ">")

def parse_hekt_header(message: str) -> Tuple[Optional[ParsedHeader], Optional[str]]:
    first_line = message.splitlines()[0].strip() if message.strip() else ""
    match = HEADER_RE.match(first_line)
    if not match:
        return None, "INVALID_HEADER_SYNTAX"
    raw_domains, raw_kv_section, action = match.groups()
    domains = re.findall(r"\[H::([A-Z]{3})\]", raw_domains)
    if not domains or any(d not in ALLOWED_DOMAINS for d in domains):
        return None, "UNKNOWN_DOMAIN"
    fields: Dict[str, str] = {}
    for token in raw_kv_section.split(" | "):
        token = token.strip()
        if "=" not in token or token.count("=") != 1:
            return None, "MALFORMED_KV_PAIR"
        key, val = token.split("=", 1)
        if not key.strip() or not val.strip():
            return None, "EMPTY_KEY_OR_VALUE"
        if any(sep in val for sep in ("|", "->")):
            return None, "UNESCAPED_DELIMITER"
        fields[key.strip()] = unescape_hekt_value(val.strip())
    return ParsedHeader(domains=domains, fields=fields, action=action), None

def is_action_allowed(header: ParsedHeader, authenticated_agent: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    allowed_union = set().union(*(DOMAIN_ACTION_MATRIX.get(d, set()) for d in header.domains))
    if header.action not in allowed_union:
        return False, "ACTION_NOT_ALLOWED_FOR_DOMAIN"
    declared_agent = header.fields.get("agent")
    if authenticated_agent and declared_agent and declared_agent != authenticated_agent:
        return False, "AGENT_IDENTITY_MISMATCH"
    for k, v in header.fields.items():
        if v.lower() in MUTABLE_ALIASES and "sha256" not in header.fields:
            return False, f"MUTABLE_ALIAS_REJECTED:{k}={v}"
    return True, None

def verify_sha256_evidence(declared_hash: Optional[str], canonical_bytes: Optional[bytes]) -> Tuple[str, Optional[str], Optional[str]]:
    if not declared_hash:
        return "UNVERIFIED", None, "MISSING_SHA256"
    norm = declared_hash.strip().lower().removeprefix("sha256:")
    if not SHA256_RE.match(norm):
        return "REJECTED", None, "INVALID_SHA256_FORMAT"
    if canonical_bytes is None:
        return "UNVERIFIED", None, "MISSING_CANONICAL_EVIDENCE"
    computed = hashlib.sha256(canonical_bytes).hexdigest()
    if not hmac.compare_digest(norm, computed):
        return "REJECTED", computed, "SHA256_MISMATCH"
    return "VALID", computed, None

def _append_witness_row(res: VerificationResult, header_line: str) -> str:
    prev_hash = "0" * 64
    if os.path.exists(LEDGER_FILE):
        with open(LEDGER_FILE, "rb") as f:
            lines = f.read().splitlines()
            if lines:
                prev_hash = hashlib.sha256(lines[-1]).hexdigest()
    rec = {"timestamp": datetime.now(timezone.utc).isoformat(), "status": res.status, "reason": res.reason, "header": header_line, "computed_sha256": res.computed_sha256, "prev_hash": prev_hash}
    rec["row_hash"] = hashlib.sha256(json.dumps(rec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec["row_hash"]

def verify_message(message: str, canonical_bytes: Optional[bytes] = None, authenticated_agent: Optional[str] = None, active_head_rev: Optional[str] = None) -> VerificationResult:
    parsed, parse_err = parse_hekt_header(message)
    if parse_err or parsed is None:
        res = VerificationResult(status="REJECTED", reason=parse_err or "PARSE_ERROR")
    else:
        allowed, auth_err = is_action_allowed(parsed, authenticated_agent=authenticated_agent)
        if not allowed:
            res = VerificationResult(status="REJECTED", reason=auth_err or "FORBIDDEN_ACTION", domains=parsed.domains, action=parsed.action)
        elif active_head_rev and parsed.fields.get("code_rev") and parsed.fields["code_rev"] != active_head_rev:
            res = VerificationResult(status="REJECTED", reason="SUPERSEDED_REV", domains=parsed.domains, action=parsed.action)
        elif "AUD" in parsed.domains or "sha256" in parsed.fields:
            ev_status, digest, ev_err = verify_sha256_evidence(parsed.fields.get("sha256"), canonical_bytes)
            res = VerificationResult(status=ev_status, reason="VERIFIED_WITH_SHA256" if ev_status == "VALID" else (ev_err or "EVIDENCE_CHECK_FAILED"), domains=parsed.domains, action=parsed.action, computed_sha256=digest)
        else:
            res = VerificationResult(status="VALID", reason="SYNTAX_AND_POLICY_VALID", domains=parsed.domains, action=parsed.action)
    res.row_hash = _append_witness_row(res, message.splitlines()[0].strip() if message.strip() else "")
    return res

def verify_external_execution(hekt_claim_header: str, target_filepath: str, observed_action: str, expected_sha256: Optional[str] = None, active_head_rev: Optional[str] = None) -> dict:
    raw = open(target_filepath, "rb").read() if os.path.exists(target_filepath) else None
    res = verify_message(hekt_claim_header, canonical_bytes=raw, active_head_rev=active_head_rev)
    if res.action and res.action != observed_action:
        res.status, res.reason = "REJECTED", f"ACTION_MISMATCH:{res.action}!={observed_action}"
    return {"verdict": "MATCH" if res.status in ("VALID", "UNVERIFIED") and raw is not None else "MISMATCH", "status": res.status, "reason": res.reason, "mismatches": [] if res.status != "REJECTED" and raw is not None else [res.reason], "row_hash": res.row_hash}

if __name__ == "__main__":
    raw_skill = open("SKILL.md", "rb").read()
    h_skill = hashlib.sha256(raw_skill).hexdigest()
    print("1. VALID:", verify_message(f"[H::AUD] sha256={h_skill} -> emit=ATTEST_ARTIFACT", canonical_bytes=raw_skill))
    print("2. REJECTED (Matriz):", verify_message("[H::AGT] agent=bot -> emit=ATTEST_ARTIFACT"))
    print("3. UNVERIFIED (Pendiente):", verify_message("[H::AUD] artifact=report.pdf -> emit=VERIFY_TRACE"))

import unicodedata
from pathlib import Path
from typing import Any

def _normalize_strings(obj: Any) -> Any:
    if isinstance(obj, str):
        return unicodedata.normalize("NFC", obj)
    if isinstance(obj, list):
        return [_normalize_strings(i) for i in obj]
    if isinstance(obj, dict):
        return {unicodedata.normalize("NFC", str(k)): _normalize_strings(v) for k, v in obj.items()}
    return obj

def canonicalize_json_bytes(data: Any) -> bytes:
    return json.dumps(_normalize_strings(data), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")

def canonicalize_text_bytes(text: str) -> bytes:
    return unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n")).encode("utf-8")

def sha256_canonical_json(data: Any) -> str:
    return hashlib.sha256(canonicalize_json_bytes(data)).hexdigest()

def sha256_canonical_text_file(file_path: str | Path) -> str:
    return hashlib.sha256(canonicalize_text_bytes(Path(file_path).read_text(encoding="utf-8"))).hexdigest()
