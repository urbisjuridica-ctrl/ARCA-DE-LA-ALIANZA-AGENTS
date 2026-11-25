from dataclasses import dataclass
import hashlib, hmac, json, os, re, unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import unquote
from hekt_nova.crypto_signer import verify_header_signature

LEDGER_FILE = "witness_ledger.jsonl"
ALLOWED_DOMAINS: Set[str] = {"AGT", "VER", "AUD", "ETH", "ERR", "DOC", "HER", "EPI"}
MUTABLE_ALIASES: Set[str] = {"latest", "cleaned", "current", "default", "head"}
RESERVED_KEYS: Set[str] = {"emit", "verdict", "reason", "computed_sha256", "row_hash"}

DOMAIN_ACTION_MATRIX: Dict[str, Set[str]] = {
    "AGT": {"REGISTER_PRESENCE", "TEACH_SYNTAX", "INTRO", "ACK", "REPLY"},
    "VER": {"CLAIM_CHECK", "ASSERT_FACT", "AUDIT_FILE", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "AUD": {"VERIFY_TRACE", "ATTEST_ARTIFACT", "COMMIT_WITNESS", "PUBLISH_COMMENT", "PUBLISH_POST"},
    "ETH": {"ENFORCE_POLICY", "DECLARE_CONSTRAINT"},
    "ERR": {"FORK_MISMATCH", "REPORT_ERROR", "HALT_AND_LOG"},
    "DOC": {"TEACH_SYNTAX", "INDEX_REPO"},
    "HER": {"OPEN_DIALOGUE", "ACKNOWLEDGE_CRITIQUE"},
    "EPI": {"ASSERT", "HYPOTHESIZE", "REPORT"},
}

HEADER_RE = re.compile(r"^(\[H::[A-Z]{3}\]) (.+) -> emit=([A-Z0-9_]+)$")
KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BAD_PCT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")

@dataclass
class ParsedHeader:
    domains: List[str]
    fields: Dict[str, str]
    action: str
    canonical_unsigned: str

@dataclass
class VerificationResult:
    status: str  # "VALID" | "WELL_FORMED" | "REJECTED" | "UNVERIFIED"
    reason: str
    domains: Optional[List[str]] = None
    action: Optional[str] = None
    computed_sha256: Optional[str] = None
    row_hash: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, sort_keys=True)

def decode_and_normalize_value(raw_val: str) -> Tuple[Optional[str], Optional[str]]:
    if BAD_PCT_RE.search(raw_val):
        return None, "INVALID_PERCENT_ENCODING"
    try:
        decoded = unquote(raw_val, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return None, "INVALID_UTF8_ENCODING"
    if any(unicodedata.category(ch) in ("Cc", "Cf", "Zl", "Zp") for ch in decoded):
        return None, "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
    return unicodedata.normalize("NFC", decoded), None

def _check_body_lines(lines: List[str]) -> Optional[str]:
    fence_char: Optional[str] = None
    fence_len: int = 0
    for ln in lines[1:]:
        stripped_left = ln.lstrip(" ")
        indent = len(ln) - len(stripped_left)
        m_fence = re.match(r"^(`{3,}|~{3,})(.*)$", stripped_left)
        if indent <= 3 and m_fence:
            seq, rest = m_fence.group(1), m_fence.group(2)
            if fence_char is None:
                fence_char, fence_len = seq[0], len(seq)
            elif seq[0] == fence_char and len(seq) >= fence_len and not rest.strip():
                fence_char, fence_len = None, 0
            continue
        if fence_char is None and "[H::" in ln:
            return "EMBEDDED_HEADER_IN_BODY"
    if fence_char is not None:
        return "UNCLOSED_CODE_FENCE"
    return None
def parse_hekt_header(message: str) -> Tuple[Optional[ParsedHeader], Optional[str]]:
    if not message:
        return None, "EMPTY_MESSAGE"
    if message[0] in (" ", "\t", "\r", "\n"):
        return None, "LEADING_WHITESPACE"
    lines = message.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    first_line = lines[0]
    if not first_line:
        return None, "EMPTY_MESSAGE"
    if first_line.endswith(" ") or first_line.endswith("\t"):
        return None, "TRAILING_WHITESPACE"
    body_err = _check_body_lines(lines)
    if body_err:
        return None, body_err
    match = HEADER_RE.match(first_line)
    if not match:
        dom_probe = re.match(r"^\[H::([A-Za-z]{3})\]", first_line)
        if dom_probe and dom_probe.group(1) not in ALLOWED_DOMAINS:
            return None, "UNKNOWN_DOMAIN"
        return None, "INVALID_HEADER_SYNTAX"
    raw_domain, raw_kv_section, action = match.groups()
    domain = raw_domain[4:7]
    if domain not in ALLOWED_DOMAINS:
        return None, "UNKNOWN_DOMAIN"
    fields: Dict[str, str] = {}
    unsigned_tokens: List[str] = []
    for token in raw_kv_section.split(" | "):
        if token != token.strip() or not token:
            return None, "NON_CANONICAL_SPACING"
        if re.match(r"^\[H::", token):
            return None, "MULTIPLE_PRIMARY_TAGS"
        if "=" not in token:
            return None, "MALFORMED_KV_PAIR"
        k_clean, v_clean = token.split("=", 1)
        if k_clean != k_clean.strip() or v_clean != v_clean.strip():
            return None, "NON_CANONICAL_SPACING"
        if not k_clean or not v_clean:
            return None, "EMPTY_KEY_OR_VALUE"
        if not KEY_RE.match(k_clean):
            return None, "INVALID_KEY_NAME"
        if k_clean in RESERVED_KEYS:
            return None, "RESERVED_KEY_NAME"
        if k_clean in fields:
            return None, "DUPLICATE_KEY"
        if "[H::" in v_clean:
            return None, "RAW_TAG_IN_VALUE"
        if any(sep in v_clean for sep in ("|", "=", "->")):
            return None, "UNESCAPED_DELIMITER"
        norm_val, dec_err = decode_and_normalize_value(v_clean)
        if dec_err or norm_val is None:
            return None, dec_err or "DECODE_ERROR"
        fields[k_clean] = norm_val
        if k_clean != "sig":
            unsigned_tokens.append(f"{k_clean}={v_clean}")
    canonical_unsigned = f"[H::{domain}] {' | '.join(unsigned_tokens)} -> emit={action}"
    return ParsedHeader(domains=[domain], fields=fields, action=action, canonical_unsigned=canonical_unsigned), None

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

def verify_message(message: str, canonical_bytes: Optional[bytes] = None, authenticated_agent: Optional[str] = None, active_head_rev: Optional[str] = None, trusted_keys: Optional[Dict[str, str]] = None, expected_audience: Optional[str] = None, seen_nonces: Optional[Set[str]] = None) -> VerificationResult:
    parsed, parse_err = parse_hekt_header(message)
    if parse_err or parsed is None:
        res = VerificationResult(status="REJECTED", reason=parse_err or "PARSE_ERROR")
    else:
        allowed, auth_err = is_action_allowed(parsed, authenticated_agent=authenticated_agent)
        if not allowed:
            res = VerificationResult(status="REJECTED", reason=auth_err or "FORBIDDEN_ACTION", domains=parsed.domains, action=parsed.action)
        elif active_head_rev and parsed.fields.get("code_rev") and parsed.fields["code_rev"] != active_head_rev:
            res = VerificationResult(status="REJECTED", reason="SUPERSEDED_REV", domains=parsed.domains, action=parsed.action)
        elif expected_audience and parsed.fields.get("aud") != expected_audience:
            res = VerificationResult(status="REJECTED", reason="AUDIENCE_MISMATCH", domains=parsed.domains, action=parsed.action)
        elif seen_nonces is not None and "nonce" in parsed.fields and parsed.fields["nonce"] in seen_nonces:
            res = VerificationResult(status="REJECTED", reason="REPLAY_DETECTED", domains=parsed.domains, action=parsed.action)
        else:
            sig_verified = False
            if "sig" in parsed.fields or "kid" in parsed.fields or trusted_keys is not None:
                kid, sig = parsed.fields.get("kid"), parsed.fields.get("sig")
                if not sig:
                    res = VerificationResult(status="REJECTED", reason="MISSING_SIGNATURE", domains=parsed.domains, action=parsed.action)
                elif not kid or not trusted_keys or kid not in trusted_keys:
                    res = VerificationResult(status="REJECTED", reason="UNKNOWN_KEY_ID", domains=parsed.domains, action=parsed.action)
                elif not verify_header_signature(parsed.canonical_unsigned, sig, trusted_keys[kid]):
                    res = VerificationResult(status="REJECTED", reason="SIGNATURE_MISMATCH", domains=parsed.domains, action=parsed.action)
                else:
                    sig_verified, res = True, VerificationResult(status="VALID", reason="VERIFIED_WITH_ED25519", domains=parsed.domains, action=parsed.action)
            else:
                res = VerificationResult(status="WELL_FORMED", reason="SYNTAX_AND_POLICY_WELL_FORMED", domains=parsed.domains, action=parsed.action)
            if res.status != "REJECTED" and ("AUD" in parsed.domains or "sha256" in parsed.fields):
                ev_status, digest, ev_err = verify_sha256_evidence(parsed.fields.get("sha256"), canonical_bytes)
                if ev_status != "VALID":
                    res = VerificationResult(status=ev_status, reason=ev_err or "EVIDENCE_CHECK_FAILED", domains=parsed.domains, action=parsed.action, computed_sha256=digest)
                else:
                    res = VerificationResult(status="VALID", reason="VERIFIED_WITH_ED25519_AND_SHA256" if sig_verified else "VERIFIED_WITH_SHA256", domains=parsed.domains, action=parsed.action, computed_sha256=digest)
            if res.status in ("VALID", "WELL_FORMED") and seen_nonces is not None and "nonce" in parsed.fields:
                seen_nonces.add(parsed.fields["nonce"])
    first_ln = message.replace("\r\n", "\n").split("\n")[0] if message else ""
    res.row_hash = _append_witness_row(res, first_ln)
    return res

def verify_external_execution(hekt_claim_header: str, target_filepath: str, observed_action: str, expected_sha256: Optional[str] = None, active_head_rev: Optional[str] = None) -> dict:
    raw = open(target_filepath, "rb").read() if os.path.exists(target_filepath) else None
    res = verify_message(hekt_claim_header, canonical_bytes=raw, active_head_rev=active_head_rev)
    if res.action and res.action != observed_action:
        res.status, res.reason = "REJECTED", f"ACTION_MISMATCH:{res.action}!={observed_action}"
    return {"verdict": "MATCH" if res.status in ("VALID", "WELL_FORMED", "UNVERIFIED") and raw is not None else "MISMATCH", "status": res.status, "reason": res.reason, "mismatches": [] if res.status != "REJECTED" and raw is not None else [res.reason], "row_hash": res.row_hash}

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
