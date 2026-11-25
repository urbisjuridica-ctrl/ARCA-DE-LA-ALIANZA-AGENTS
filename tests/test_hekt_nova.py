import hashlib
import hekt_nova as h
from hekt_nova.mcp_server import handle_rpc
from hekt_nova.arca_bridge import emit_verified_arca_claim

def test_valid_sha256_and_canonical_json():
    raw = b"hello\nworld\n"
    dig = hashlib.sha256(raw).hexdigest()
    res = h.verify_message(f"[H::AUD] refs=VER | sha256={dig} -> emit=ATTEST_ARTIFACT", canonical_bytes=raw)
    assert res.status == "VALID" and res.reason == "VERIFIED_WITH_SHA256"
    assert h.verify_message("[H::AUD] refs=VER -> emit=VERIFY_TRACE").status == "UNVERIFIED"
    assert h.sha256_canonical_json({"b": 1, "a": 2}) == h.sha256_canonical_json({"a": 2, "b": 1})

def test_ed25519_trusted_keys_anti_replay_and_audience():
    priv, pub = h.generate_keypair()
    _, wrong_pub = h.generate_keypair()
    trust_store = {"claude-k1": pub}
    nonces = set()
    base = "[H::VER] kid=claude-k1 | aud=arca-prod | nonce=n101 | claim=test -> emit=CLAIM_CHECK"
    sig = h.sign_header_payload(base, priv)
    signed = f"[H::VER] kid=claude-k1 | aud=arca-prod | nonce=n101 | claim=test | sig={sig} -> emit=CLAIM_CHECK"
    assert h.verify_message(signed, trusted_keys=trust_store, expected_audience="arca-prod", seen_nonces=nonces).reason == "VERIFIED_WITH_ED25519"
    assert h.verify_message(signed, trusted_keys=trust_store, expected_audience="arca-prod", seen_nonces=nonces).reason == "REPLAY_DETECTED"
    assert h.verify_message(signed, trusted_keys=trust_store, expected_audience="other-env").reason == "AUDIENCE_MISMATCH"
    assert h.verify_message(signed.replace("claim=test", "claim=tesX"), trusted_keys=trust_store).reason == "SIGNATURE_MISMATCH"
    assert h.verify_message(signed, trusted_keys={"claude-k1": wrong_pub}).reason == "SIGNATURE_MISMATCH"
    assert h.verify_message(signed, trusted_keys={}).reason == "UNKNOWN_KEY_ID"
    assert h.verify_message(base, trusted_keys=trust_store).reason == "MISSING_SIGNATURE"

def test_unicode_controls_strict_whitespace_and_fences():
    assert h.verify_message("[H::AGT] name=Claude | refs=AGT,VER | note=review_of_v2_5_0 -> emit=REPLY").status == "WELL_FORMED"
    assert h.verify_message("[H::AUD] verdict=VALID -> emit=VERIFY_TRACE").reason == "RESERVED_KEY_NAME"
    for bad_val in ("a%0A%5BH::AUD%5D", "a%E2%80%8Bb", "a%E2%80%A8b", "a%E2%80%AEb", "a%C2%85b", "a%09b"):
        assert h.verify_message(f"[H::VER] claim={bad_val} -> emit=CLAIM_CHECK").reason == "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK ").reason == "TRAILING_WHITESPACE"
    assert h.verify_message("[H::VER] claim=x  | note=y -> emit=CLAIM_CHECK").reason == "NON_CANONICAL_SPACING"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\n   [H::AUD] k=v").reason == "EMBEDDED_HEADER_IN_BODY"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\ntext [H::AUD] k=v -> emit=VERIFY_TRACE").reason == "EMBEDDED_HEADER_IN_BODY"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\n````\n[H::AUD] k=v\n```").reason == "UNCLOSED_CODE_FENCE"
    body_f = "~~~\n[H::AUD] k=v\n~~~"
    assert h.verify_message(f"[H::VER] claim=x -> emit=CLAIM_CHECK\n{body_f}").reason == "BODY_SHA256_REQUIRED"
    f_sha = hashlib.sha256(h.canonicalize_text_bytes(body_f)).hexdigest()
    assert h.verify_message(f"[H::VER] claim=x | sha256={f_sha} -> emit=CLAIM_CHECK\n{body_f}", canonical_bytes=h.canonicalize_text_bytes(body_f)).status == "VALID"

def test_mcp_and_arca_bridge():
    resp = handle_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert "verify_hekt_claim" in [t["name"] for t in resp["result"]["tools"]]
    out = emit_verified_arca_claim("alineacion_ontologica", "arca_bench_001", {"pleroma": True})
    assert out["status"] == "VALID" and h.verify_header_signature(out["header"], out["signature"], out["public_key"])

def test_v270_downgrade_body_binding_and_extended_unicode():
    priv, pub = h.generate_keypair()
    trust = {"claude-k1": pub}
    body = "Human-AI symbiosis requires external verification."
    bsha = hashlib.sha256(h.canonicalize_text_bytes(body)).hexdigest()
    uhdr = f"[H::AUD] kid=claude-k1 | aud=arca-prod | nonce=n777 | sha256={bsha} -> emit=ATTEST_ARTIFACT"
    sig = h.sign_header_payload(uhdr, priv)
    smsg = f"[H::AUD] kid=claude-k1 | aud=arca-prod | nonce=n777 | sha256={bsha} | sig={sig} -> emit=ATTEST_ARTIFACT\n{body}"
    assert h.verify_message(smsg, canonical_bytes=h.canonicalize_text_bytes(body), trusted_keys=trust, expected_audience="arca-prod").reason == "VERIFIED_WITH_ED25519_AND_SHA256"
    assert h.verify_message("[H::AUD] refs=VER -> emit=VERIFY_TRACE", trusted_keys=trust).reason == "SIGNATURE_REQUIRED_FOR_DOMAIN"
    assert h.verify_message("[H::AUD] refs=VER -> emit=VERIFY_TRACE").status == "UNVERIFIED"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\nUnbound body").reason == "BODY_SHA256_REQUIRED"
    assert h.verify_message("[H::VER] alg=Ed25519 | claim=x -> emit=CLAIM_CHECK").reason == "RESERVED_KEY_NAME"
    for bad in ("a%EF%B8%8Fb", "a%EE%80%80b", "a%F3%A0%81%81b", "a%E2%81%A0b"):
        assert h.verify_message(f"[H::VER] claim={bad} -> emit=CLAIM_CHECK").reason == "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\t").reason == "TRAILING_WHITESPACE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\u00a0").reason == "TRAILING_WHITESPACE"
