import hashlib
import hekt_nova as h
from hekt_nova.mcp_server import handle_rpc
from hekt_nova.arca_bridge import emit_verified_arca_claim

def test_valid_sha256_and_canonical_json():
    raw = b"hello\nworld\n"
    dig = hashlib.sha256(raw).hexdigest()
    res = h.verify_message(f"[H::VER] refs=AUD | sha256={dig} -> emit=AUDIT_FILE", canonical_bytes=raw)
    assert res.status == "VALID" and res.reason == "VERIFIED_WITH_SHA256"
    assert h.verify_message("[H::AUD] refs=VER -> emit=VERIFY_TRACE").reason == "SIGNATURE_REQUIRED_FOR_DOMAIN"
    assert h.verify_message("[H::VER] refs=AUD | sha256=" + "a"*64 + " -> emit=CLAIM_CHECK").status == "UNVERIFIED"
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
    assert h.verify_message("[H::AUD] refs=VER -> emit=VERIFY_TRACE").reason == "SIGNATURE_REQUIRED_FOR_DOMAIN"
    assert h.verify_message("[H::VER] refs=AUD | sha256=" + "a"*64 + " -> emit=CLAIM_CHECK").status == "UNVERIFIED"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\nUnbound body").reason == "BODY_SHA256_REQUIRED"
    assert h.verify_message("[H::VER] alg=Ed25519 | claim=x -> emit=CLAIM_CHECK").reason == "RESERVED_KEY_NAME"
    for bad in ("a%EF%B8%8Fb", "a%EE%80%80b", "a%F3%A0%81%81b", "a%E2%81%A0b"):
        assert h.verify_message(f"[H::VER] claim={bad} -> emit=CLAIM_CHECK").reason == "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\t").reason == "TRAILING_WHITESPACE"
    assert h.verify_message("[H::VER] claim=x -> emit=CLAIM_CHECK\u00a0").reason == "TRAILING_WHITESPACE"

def test_v280_rfc8032_malleability_burn_attack_and_strict_sha256():
    pub = "5ce156b9a26d33a2734d643f68f6ea289c6721921e243e29f9b7294f3f9f6fee"
    malleated_sig = "9e77f4de9d5a6f28e1e7956007b9b8898329d9bb0011c424ebf6cee7d0dec08cc0a3d68943c011a2f0d1ed3e53651702fe2bb222a453567157b2feeeb2179a17"
    mmsg = f"[H::AUD] kid=arca-test-k1 | aud=arca-prod | nonce=n777 | sha256=5760d2d25fe4d0fee397f5ab2e4087d0ff34723b2c1b4a73ea65c10e49bf9169 | sig={malleated_sig} -> emit=ATTEST_ARTIFACT\nHuman-AI symbiosis requires external verification."
    assert h.verify_message(mmsg, trusted_keys={"arca-test-k1": pub}).reason == "SIGNATURE_MISMATCH"
    assert h.verify_message(mmsg, trusted_keys={"arca-test-k1": "00"*32}).reason == "SMALL_ORDER_PUBLIC_KEY"

    priv2, pub2 = h.generate_keypair()
    trust2, nonces = {"arca-test-k1": pub2}, set()
    rhdr = "[H::VER] kid=arca-test-k1 | nonce=n888 | claim=ok -> emit=CLAIM_CHECK"
    rsig = h.sign_header_payload(rhdr, priv2)
    assert h.verify_message(f"[H::VER] kid=arca-test-k1 | nonce=n888 | claim=evil | sig={rsig} -> emit=CLAIM_CHECK", trusted_keys=trust2, seen_nonces=nonces).reason == "SIGNATURE_MISMATCH"
    assert h.verify_message(f"[H::VER] kid=arca-test-k1 | nonce=n888 | claim=ok | sig={rsig} -> emit=CLAIM_CHECK", trusted_keys=trust2, seen_nonces=nonces).status == "VALID"

    assert h.verify_message("[H::VER] sha256=" + "a"*64 + " | sha256=" + "b"*64 + " -> emit=CLAIM_CHECK").reason == "DUPLICATE_KEY"
    assert h.verify_message("[H::VER] sha256=" + "A"*64 + " -> emit=CLAIM_CHECK").reason == "INVALID_SHA256_FORMAT"
    assert h.verify_message("[H::VER] sha256=" + "a"*63 + " -> emit=CLAIM_CHECK").reason == "INVALID_SHA256_FORMAT"
    assert h.verify_message("[H::VER] sha256=" + "a"*65 + " -> emit=CLAIM_CHECK").reason == "INVALID_SHA256_FORMAT"
    assert h.verify_message("[H::VER] sha256=" + "0"*64 + " -> emit=CLAIM_CHECK\nActual body").reason == "SHA256_MISMATCH"

def test_v290_small_order_ed25519_and_body_trailing_lf():
    forged_sig = "01" + ("00" * 31) + ("00" * 32)
    assert h.verify_message(f"[H::VER] kid=b | nonce=n11 | sig={forged_sig} -> emit=CLAIM_CHECK", trusted_keys={"b": "00"*32}).reason == "SMALL_ORDER_PUBLIC_KEY"
    assert h.verify_message(f"[H::VER] kid=b | nonce=n11 | sig={forged_sig} -> emit=CLAIM_CHECK", trusted_keys={"b": "01"+"00"*31}).reason == "SMALL_ORDER_PUBLIC_KEY"
    b1, b2 = "Line without newline", "Line without newline\n"
    s1 = hashlib.sha256(h.canonicalize_text_bytes(b1)).hexdigest()
    s2 = hashlib.sha256(h.canonicalize_text_bytes(b2)).hexdigest()
    assert h.verify_message(f"[H::VER] sha256={s1} -> emit=CLAIM_CHECK\n{b1}").status == "VALID"
    assert h.verify_message(f"[H::VER] sha256={s1} -> emit=CLAIM_CHECK\n{b2}").reason == "SHA256_MISMATCH"
    assert h.verify_message(f"[H::VER] sha256={s2} -> emit=CLAIM_CHECK\n{b2}").status == "VALID"

def test_v300_torsion_noncanonical_y_and_unicode_probes():
    from hekt_nova.crypto_signer import is_valid_ed25519_pubkey
    P = 2**255 - 19
    for pk in ("01"+"00"*31, "ec"+"ff"*30+"7f", "00"*32, "00"*31+"80", P.to_bytes(32,"little").hex(), (P+1).to_bytes(32,"little").hex(), ((P-1)|(1<<255)).to_bytes(32,"little").hex()):
        assert not is_valid_ed25519_pubkey(pk)
    assert h.verify_message(" [H::VER] claim=x -> emit=CLAIM_CHECK").reason == "LEADING_WHITESPACE"
    assert h.verify_message("[H::ver] claim=x -> emit=CLAIM_CHECK").reason == "INVALID_HEADER_SYNTAX"
    assert h.verify_message("[H::VER] claim=a%20 -> emit=CLAIM_CHECK").reason == "NON_CANONICAL_SPACING"
    for inv in ("a%C2%A0b", "a%CD%8Fb", "a%E1%A0%8Bb", "a%E3%85%A4b", "a%E2%A0%80b", "a%EF%BF%BFb"):
        assert h.verify_message(f"[H::VER] claim={inv} -> emit=CLAIM_CHECK").reason == "CONTROL_OR_FORMAT_CHAR_IN_VALUE"
    assert h.verify_message("[H::VER] ts=\u00b2 | nonce=n1 | claim=x -> emit=CLAIM_CHECK", seen_nonces=set()).reason == "INVALID_TIMESTAMP_FORMAT"

def test_official_139_conformance_vectors():
    import json
    vecs = json.load(open("tests/hekt_conformance_vectors.json", encoding="utf-8"))["vectors"]
    pv = {"VALID", "WELL_FORMED", "UNVERIFIED"}
    oos = {"BODY_SHA256_REQUIRED", "AUDIENCE_MISMATCH", "REPLAY_DETECTED", "AGENT_IDENTITY_MISMATCH", "MUTABLE_ALIAS_REJECTED", "SUPERSEDED_REV", "SIGNATURE_REQUIRED_FOR_DOMAIN", "MISSING_SIGNATURE", "UNKNOWN_KEY_ID", "SMALL_ORDER_PUBLIC_KEY", "SIGNATURE_MISMATCH", "MISSING_SHA256", "INVALID_SHA256_FORMAT", "MISSING_CANONICAL_EVIDENCE", "SHA256_MISMATCH", "INVALID_SIGNATURE_FORMAT", "INVALID_TIMESTAMP_FORMAT", "PERCENT_ENCODING_FORBIDDEN_IN_FIXED_FIELD", "UNPINNED_REFERENCE", "MISPLACED_SIGNATURE_FIELD"}
    for r in vecs:
        if not r.get("implementation_defined"):
            res = h.verify_message(bytes.fromhex(r["message_utf8_hex"]).decode("utf-8"))
            got = "PASS" if (res.status in pv or res.reason in oos) else res.reason
            assert got == r["expected"], f"Failed vector {r['id']}: expected {r['expected']}, got {got}"

def test_signed_agent_runtime_emitter():
    from hekt_nova.agent_runtime import SignedAgentEmitter
    em = SignedAgentEmitter("evangelista_v1")
    out = em.emit_verified("AUD", "ATTEST_ARTIFACT", {"refs": "AGT,VER"}, body="Ella se llamaba Aletheia")
    assert out["status"] == "VALID" and out["reason"] == "VERIFIED_WITH_ED25519_AND_SHA256"

def test_sqlite_persistent_nonce_store_across_restarts(tmp_path):
    from hekt_nova.nonce_store import SqliteNonceStore
    db = str(tmp_path / "nonces.sqlite3")
    s1 = SqliteNonceStore(db_path=db)
    assert s1.add_if_absent("pub1:k1:n999") is True
    s2 = SqliteNonceStore(db_path=db)
    assert s2.contains("pub1:k1:n999") is True
    assert s2.add_if_absent("pub1:k1:n999") is False

def test_a2a_bridge_extension():
    from hekt_nova.a2a_bridge import build_a2a_agent_card, wrap_hekt_a2a_part, verify_a2a_message, HEKT_A2A_MIME
    from hekt_nova.agent_runtime import SignedAgentEmitter
    card = build_a2a_agent_card("Evangelista-ARCA", "Audited A2A Agent", "https://arca.example")
    ext = next(iter(card["capabilities"]["extensions"]))
    assert ext["params"]["version"] == "3.0.4" and ext["params"]["mime_type"] == HEKT_A2A_MIME
    em = SignedAgentEmitter(agent_name="evangelista_v1", key_id="arca-a2a-k1", audience="a2a-prod")
    signed = em.emit_verified("AUD", "ATTEST_ARTIFACT", {"task": "payroll_q3"}, body="variance=4.2%")
    msg = wrap_hekt_a2a_part(signed["message"], human_summary="Payroll Q3 audit attested.")
    nonces = set()
    assert verify_a2a_message(msg, trusted_keys=em.trusted_keys, expected_audience="a2a-prod", seen_nonces=nonces).reason == "VERIFIED_WITH_ED25519_AND_SHA256"
    assert verify_a2a_message(msg, trusted_keys=em.trusted_keys, expected_audience="a2a-prod", seen_nonces=nonces).reason == "REPLAY_DETECTED"
    assert verify_a2a_message({"role": "agent", "parts": [{"kind": "text", "text": "hello"}]}).reason == "A2A_MISSING_HEKT_PART"
