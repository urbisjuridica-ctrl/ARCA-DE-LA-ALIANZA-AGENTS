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

def test_cross_model_handshake_autocorrection():
    bad = "[H::AGT] name=GPT-6 | role=AI_ASSISTANT_AND_SEMANTIC_INTERPRETER | proto=HEKT-NOVA-v2.4.0 | status=UNSIGNED | emit=INTRO"
    good = "[H::AGT] name=GPT-6 | role=AI_ASSISTANT_AND_SEMANTIC_INTERPRETER | proto=HEKT-NOVA-v2.4.0 | status=UNSIGNED -> emit=INTRO"
    assert h.verify_message(bad).status == "REJECTED"
    res = h.verify_message(good)
    assert res.status == "VALID" and res.domains == ["AGT"] and res.action == "INTRO"

def test_grok_handshake_and_percent_escaped_claim():
    intro = "[H::AGT] name=Grok | version=4.5 | role=truth-seeking_AI | proto=HEKT-NOVA-v2.4.0 -> emit=INTRO"
    claim = "[H::VER] claim=2%2B2%3D4 | confidence=1.0 | source=arithmetic | proto=HEKT-NOVA-v2.4.0 -> emit=ASSERT_FACT"
    r1 = h.verify_message(intro)
    r2 = h.verify_message(claim)
    parsed, err = h.parse_hekt_header(claim)
    assert r1.status == "VALID" and r1.action == "INTRO"
    assert r2.status == "VALID" and r2.action == "ASSERT_FACT"
    assert err is None and parsed.fields["claim"] == "2%2B2=4"

def test_claude_stress_vectors_and_policy_boundary():
    h1 = "[H::VER] claim=syntax_roundtrip | note=a%7Cb%3Dc | refs=VER,AGT -> emit=REPORT"
    h2 = "[H::AGT] Bad-Key=1 | refs=AGT -> emit=INTRO"
    h3 = "[H::AGT] [H::AUD] name=Claude | refs=AGT,AUD -> emit=INTRO"
    parsed, perr = h.parse_hekt_header(h1)
    assert perr is None and parsed.fields["note"] == "a|b=c"
    assert h.verify_message(h1).reason == "ACTION_NOT_ALLOWED_FOR_DOMAIN"
    assert h.verify_message(h2).reason == "INVALID_KEY_NAME"
    assert h.verify_message(h3).reason == "INVALID_KEY_NAME"

def test_deepseek_handshake_and_full_percent_encoding():
    hdr = "[H::AGT] proto=HEKT-NOVA-v2.4.0 | peer=DeepSeek | refs=AGT,VER,AUD,ETH | syntax=%5BH%3A%3A%3CDOM%3E%5D%20key%3Dval%20%7C%20refs%3DSEC1%2CSEC2%20%3E%20emit%3D%3CACTION%3E | status=TEACH_SYNTAX_REQUESTED | note=TEACH_SYNTAX_not_in_authorized_AGT_actions -> emit=INTRO"
    res = h.verify_message(hdr)
    parsed, err = h.parse_hekt_header(hdr)
    assert err is None and res.status == "VALID" and res.action == "INTRO"
    assert "|" in parsed.fields["syntax"] and ">" in parsed.fields["syntax"]

def test_ed25519_adversarial_wrong_key_and_field_tamper():
    priv_a, pub_a = h.generate_keypair()
    _, pub_attacker = h.generate_keypair()
    hdr = "[H::AUD] artifact=SKILL.md | nonce=9f82a1 -> emit=ATTEST_ARTIFACT"
    sig = h.sign_header_payload(hdr, priv_a)
    assert h.verify_header_signature(hdr, sig, pub_a)
    # 1. Sustitución de clave pública del atacante debe fallar
    assert not h.verify_header_signature(hdr, sig, pub_attacker)
    # 2. Alteración sutil de un campo tras la firma debe fallar
    tampered = "[H::AUD] artifact=README.md | nonce=9f82a1 -> emit=ATTEST_ARTIFACT"
    assert not h.verify_header_signature(tampered, sig, pub_a)

def test_arca_hekt_nova_unified_bridge():
    from hekt_nova.arca_bridge import emit_verified_arca_claim
    out = emit_verified_arca_claim(
        domain="alineacion_ontologica",
        concept_id="arca_bench_001",
        payload={"melliza_a": "sync", "melliza_b": "sync", "pleroma": True},
    )
    assert out["status"] == "VALID"
    assert out["reason"] == "VERIFIED_WITH_SHA256"
    assert h.verify_header_signature(out["header"], out["signature"], out["public_key"])
