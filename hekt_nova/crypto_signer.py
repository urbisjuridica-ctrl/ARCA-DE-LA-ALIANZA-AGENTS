import hashlib, hmac, os
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    HAS_ED25519 = True
except ImportError:
    HAS_ED25519 = False

def generate_keypair() -> Tuple[str, str]:
    """Devuelve (private_hex, public_hex) en Ed25519 real (o HMAC-SHA256 fallback)."""
    if HAS_ED25519:
        priv = Ed25519PrivateKey.generate()
        pub = priv.public_key()
        priv_b = priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
        pub_b = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return priv_b.hex(), pub_b.hex()
    seed = os.urandom(32).hex()
    return seed, hashlib.sha256(seed.encode()).hexdigest()

def sign_header_payload(header_without_sig: str, private_hex: str) -> str:
    msg = header_without_sig.strip().encode("utf-8")
    if HAS_ED25519:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex))
        return priv.sign(msg).hex()
    pub_hex = hashlib.sha256(private_hex.encode()).hexdigest()
    return hmac.new(bytes.fromhex(pub_hex), msg, hashlib.sha256).hexdigest()

def verify_header_signature(header_without_sig: str, sig_hex: str, public_hex: str) -> bool:
    msg = header_without_sig.strip().encode("utf-8")
    try:
        if HAS_ED25519:
            pub = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex))
            pub.verify(bytes.fromhex(sig_hex), msg)
            return True
        expected = hmac.new(bytes.fromhex(public_hex), msg, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig_hex.lower())
    except Exception:
        return False
