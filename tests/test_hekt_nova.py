import hashlib, json
import hekt_nova as h
from hekt_nova.mcp_server import handle_rpc

def test_valid_sha256_and_canonical_json():
    raw = b"hello\nworld\n"
    dig = hashlib.sha256(raw).hexdigest()
    res = h.verify_message(f"[H::AUD] refs=VER | sha256={dig} -> emit=ATTEST_ARTIFACT", canonical_bytes=raw)
    assert res.status == "VALID"
    assert h.sha256_canonical_json({"b": 1, "a": 2}) == h.sha256_canonical_json({"a": 2, "b": 1})

def test_reject_stacked_domains_and_matrix_violation():
    assert h.parse_hekt_header("[H::VER] [H::AUD] a=1 -> emit=CLAIM_CHECK") == (None, "INVALID_KEY_NAME")
    res = h.verify_message("[H::AGT] agent=bot -> emit=ATTEST_ARTIFACT")
    assert res.status == "REJECTED" and res.reason == "ACTION_NOT_ALLOWED_FOR_DOMAIN"

def test_ed25519_signature_roundtrip():
    priv, pub = h.generate_keypair()
    hdr = "[H::AUD] artifact=SKILL.md -> emit=ATTEST_ARTIFACT"
    sig = h.sign_header_payload(hdr, priv)
    assert h.verify_header_signature(hdr, sig, pub)
    assert not h.verify_header_signature(hdr + "x", sig, pub)

def test_mcp_server_rpc():
    resp = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = [t["name"] for t in resp["result"]["tools"]]
    assert "verify_hekt_claim" in tools and "canonical_sha256" in tools
