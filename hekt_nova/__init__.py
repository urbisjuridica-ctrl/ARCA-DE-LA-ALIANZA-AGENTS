from hekt_external_verifier import (
    verify_message,
    verify_external_execution,
    parse_hekt_header,
    canonicalize_json_bytes,
    canonicalize_text_bytes,
    sha256_canonical_json,
    sha256_canonical_text_file,
)
from .crypto_signer import generate_keypair, sign_header_payload, verify_header_signature, HAS_ED25519

__version__ = "2.4.0"
