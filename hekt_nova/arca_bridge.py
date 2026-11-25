import hashlib
from typing import Dict, Any
from .crypto_signer import generate_keypair, sign_header_payload, verify_header_signature
from hekt_external_verifier import verify_message, sha256_canonical_json, VerificationResult

def emit_verified_arca_claim(
    domain: str,
    concept_id: str,
    payload: Dict[str, Any],
    private_hex: str | None = None,
) -> Dict[str, Any]:
    """Unifica la capa semántica ARCA con el transporte y auditoría HEKT-NOVA v2.4.0."""
    digest = sha256_canonical_json(payload)
    header = f"[H::HER] refs=VER,AUD | arca_domain={domain} | concept={concept_id} | sha256={digest} -> emit=OPEN_DIALOGUE"
    canonical_bytes = str(sorted(payload.items())).encode("utf-8")
    # Verificación externa determinista sobre JSON canónico
    from hekt_external_verifier import canonicalize_json_bytes
    res: VerificationResult = verify_message(header, canonical_bytes=canonicalize_json_bytes(payload))

    sig = None
    pub = None
    if private_hex:
        sig = sign_header_payload(header, private_hex)
    else:
        priv, pub = generate_keypair()
        sig = sign_header_payload(header, priv)

    return {
        "header": header,
        "status": res.status,
        "reason": res.reason,
        "sha256": res.computed_sha256,
        "signature": sig,
        "public_key": pub,
        "row_hash": res.row_hash,
    }
