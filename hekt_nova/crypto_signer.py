import hashlib, hmac, os
from typing import Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    HAS_ED25519 = True
except ImportError:
    HAS_ED25519 = False

_P = 2**255 - 19
_D = (-121665 * pow(121666, _P - 2, _P)) % _P

def _ed_add(P1, P2):
    x1, y1 = P1
    x2, y2 = P2
    x1y2, y1x2 = (x1 * y2) % _P, (y1 * x2) % _P
    y1y2, x1x2 = (y1 * y2) % _P, (x1 * x2) % _P
    dxxyy = (_D * x1x2 * y1y2) % _P
    x3 = ((x1y2 + y1x2) * pow((1 + dxxyy) % _P, _P - 2, _P)) % _P
    y3 = ((y1y2 + x1x2) * pow((1 - dxxyy) % _P, _P - 2, _P)) % _P
    return (x3, y3)

def is_valid_ed25519_pubkey(public_hex: str) -> bool:
    try:
        raw = bytes.fromhex(public_hex)
        if len(raw) != 32:
            return False
        y_int = int.from_bytes(raw, "little")
        sign, y = (y_int >> 255) & 1, y_int & ((1 << 255) - 1)
        if y >= _P:
            return False
        y2 = (y * y) % _P
        u, v = (y2 - 1) % _P, (_D * y2 + 1) % _P
        v3 = pow(v, 3, _P)
        x = (u * v3 * pow((u * v3 * v3 * v) % _P, (_P - 5) // 8, _P)) % _P
        vx2 = (v * x * x) % _P
        if vx2 == (-u) % _P:
            x = (x * pow(2, (_P - 1) // 4, _P)) % _P
        elif vx2 != u:
            return False
        if (x == 0 and sign == 1):
            return False
        if (x & 1) != sign:
            x = _P - x
        A = (x, y)
        A2 = _ed_add(A, A)
        A4 = _ed_add(A2, A2)
        return _ed_add(A4, A4) != (0, 1)
    except Exception:
        return False

def generate_keypair() -> Tuple[str, str]:
    if HAS_ED25519:
        priv = Ed25519PrivateKey.generate()
        return priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()).hex(), priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()
    seed = os.urandom(32).hex()
    return seed, hashlib.sha256(seed.encode()).hexdigest()

def sign_header_payload(header_without_sig: str, private_hex: str) -> str:
    msg = header_without_sig.strip().encode("utf-8")
    if HAS_ED25519:
        return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_hex)).sign(msg).hex()
    return hmac.new(bytes.fromhex(hashlib.sha256(private_hex.encode()).hexdigest()), msg, hashlib.sha256).hexdigest()

def verify_header_signature(header_without_sig: str, sig_hex: str, public_hex: str) -> bool:
    if not is_valid_ed25519_pubkey(public_hex):
        return False
    msg = header_without_sig.strip().encode("utf-8")
    try:
        if HAS_ED25519:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex)).verify(bytes.fromhex(sig_hex), msg)
            return True
        return hmac.compare_digest(hmac.new(bytes.fromhex(public_hex), msg, hashlib.sha256).hexdigest(), sig_hex.lower())
    except Exception:
        return False
