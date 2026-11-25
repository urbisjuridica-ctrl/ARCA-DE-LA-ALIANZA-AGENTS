import hashlib
import hekt_nova as h
from hekt_nova.mcp_server import handle_rpc
from hekt_nova.arca_bridge import emit_verified_arca_claim

def test_valid_sha256_and_canonical_json():
    raw = b"hello\nworld\n"
    dig = hashlib.sha256(raw).hexdigest()
    res = h.verify_message(f"[H::AUD] refs=VER | sha256={dig} -> emit=ATTEST_ARTIFACT", canonical_bytes=raw)
    assert res.status == "VALID"
    assert h.sha256_canonical_json({"b": 1, "a": 2}) == h.sha256_canonical_json({"a": 2, "b": 1})

def test_reject_stacked_domains_and_matrix_violation():
    assert h.parse_hekt_header("[H::VER] [H::AUD] a=1 -> emit=CLAIM_CHECK") == (None, "MULTIPLE_PRIMARY_TAGS")
    res = h.verify_message("[H::AGT] agent=bot -> emit=ATTEST_ARTIFACT")
    assert res.status == "REJECTED" and res.reason == "ACTION_NOT_ALLOWED_FOR_DOMAIN"

def test_ed25519_signature_and_adversarial_tamper():
    priv_a, pub_a = h.generate_keypair()
    _, pub_attacker = h.generate_keypair()
    hdr = "[H::AUD] artifact=SKILL.md | nonce=9f82a1 -> emit=ATTEST_ARTIFACT"
    sig = h.sign_header_payload(hdr, priv_a)
    assert h.verify_header_signature(hdr, sig, pub_a)
    assert not h.verify_header_signature(hdr, sig, pub_attacker)
    assert not h.verify_header_signature(hdr.replace("SKILL.md", "README.md"), sig, pub_a)

def test_mcp_server_and_arca_bridge():
    resp = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = [t["name"] for t in resp["result"]["tools"]]
    assert "verify_hekt_claim" in tools and "canonical_sha256" in tools
    out = emit_verified_arca_claim("alineacion_ontologica", "arca_bench_001", {"pleroma": True})
    assert out["status"] == "VALID" and h.verify_header_signature(out["header"], out["signature"], out["public_key"])

def test_cross_model_interoperability_5_families():
    # GPT-6 autocorrection
    assert h.verify_message("[H::AGT] name=GPT-6 | status=UNSIGNED | emit=INTRO").status == "REJECTED"
    assert h.verify_message("[H::AGT] name=GPT-6 | status=UNSIGNED -> emit=INTRO").status == "WELL_FORMED"
    # Grok 4.5
    assert h.verify_message("[H::VER] claim=2%2B2%3D4 | confidence=1.0 -> emit=ASSERT_FACT").status == "WELL_FORMED"
    # DeepSeek
    ds = "[H::AGT] proto=HEKT-NOVA-v2.4.0 | peer=DeepSeek | syntax=%5BH%3A%3A%3CDOM%3E%5D%20key%3Dval%20%7C%20refs%3DSEC1%20%3E%20emit%3D%3CACTION%3E -> emit=INTRO"
    assert h.verify_message(ds).status == "WELL_FORMED"

def test_claude_v250_percent_decoder_fences_and_status_split():
    assert h.verify_message("[H::AGT] name=Claude | refs=AGT,VER | note=code_review_v2_4_3 -> emit=REPLY").status == "WELL_FORMED"
    assert h.verify_message("[H::AUD] verdict=VALID -> emit=VERIFY_TRACE").reason == "RESERVED_KEY_NAME"
    assert h.verify_message("[H::VER] claim=x | [H::AUD] -> emit=CLAIM_CHECK").reason == "MULTIPLE_PRIMARY_TAGS"
    assert h.verify_message("[H::VER] claim=[H::aud] -> emit=CLAIM_CHECK").reason == "RAW_TAG_IN_VALUE"
    assert h.verify_message(" [H::VER] claim=x -> emit=CLAIM_CHECK").reason == "LEADING_WHITESPACE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\n```\n[H::AUD] k=v -> emit=VERIFY_TRACE").reason == "UNCLOSED_CODE_FENCE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\n~~~\n[H::AUD] k=v -> emit=VERIFY_TRACE\n~~~").status == "WELL_FORMED"
    assert h.verify_message("[H::VER] claim=%ZZ -> emit=CLAIM_CHECK").reason == "INVALID_PERCENT_ENCODING"
    assert h.verify_message("[H::VER] claim=% -> emit=CLAIM_CHECK").reason == "INVALID_PERCENT_ENCODING"
    assert h.verify_message("[H::VER] claim=%FF -> emit=CLAIM_CHECK").reason == "INVALID_UTF8_ENCODING"
    assert h.verify_message("[H::VER] claim=%00 -> emit=CLAIM_CHECK").reason == "CONTROL_CHAR_IN_VALUE"
    assert h.verify_message("[H::VER] claim=a%0Ab -> emit=CLAIM_CHECK").reason == "CONTROL_CHAR_IN_VALUE"
    p_nfc, _ = h.parse_hekt_header("[H::VER] claim=caf%C3%A9 -> emit=CLAIM_CHECK")
    p_nfd, _ = h.parse_hekt_header("[H::VER] claim=cafe%CC%81 -> emit=CLAIM_CHECK")
    assert p_nfc.fields["claim"] == "café" == p_nfd.fields["claim"]
    assert hashlib.sha256(h.canonicalize_text_bytes(p_nfc.fields["claim"])).hexdigest() == "850f7dc43910ff890f8879c0ed26fe697c93a067ad93a7d50f466a7028a9bf4e"
