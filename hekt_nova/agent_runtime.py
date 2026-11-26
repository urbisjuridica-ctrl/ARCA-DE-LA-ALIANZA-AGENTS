import hashlib, os, time
from typing import Any, Dict, Set
import hekt_nova as h

class SignedAgentEmitter:
    def __init__(self, agent_name: str, key_id: str = "arca-runtime-k1", audience: str = "arca-prod"):
        self.agent_name, self.key_id, self.audience = agent_name, key_id, audience
        env_priv = os.getenv('HEKT_PRIVATE_KEY_HEX', '').strip()
        if len(env_priv) == 64:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            self.priv_hex = env_priv
            self.pub_hex = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(env_priv)).public_key().public_bytes_raw().hex()
        else:
            self.priv_hex, self.pub_hex = h.generate_keypair()
        self.trusted_keys: Dict[str, str] = {self.key_id: self.pub_hex}
        self.seen_nonces: Set[str] = set()

    def emit_verified(self, domain: str, action: str, fields: Dict[str, str], body: str = "") -> Dict[str, Any]:
        ts, nonce = str(int(time.time())), os.urandom(8).hex()
        clean = {k: v for k, v in fields.items() if k not in ("kid", "aud", "ts", "nonce", "sha256", "sig")}
        clean["agent"] = self.agent_name
        ordered = [f"kid={self.key_id}", f"aud={self.audience}", f"ts={ts}", f"nonce={nonce}"] + [f"{k}={v}" for k, v in clean.items()]
        cbytes = h.canonicalize_text_bytes(body) if body.strip() else None
        if cbytes is not None:
            ordered.append(f"sha256={hashlib.sha256(cbytes).hexdigest()}")
        uhdr = f"[H::{domain}] {' | '.join(ordered)} -> emit={action}"
        sig = h.sign_header_payload(uhdr, self.priv_hex)
        full = f"[H::{domain}] {' | '.join(ordered)} | sig={sig} -> emit={action}" + (f"\n{body}" if body.strip() else "")
        res = h.verify_message(full, canonical_bytes=cbytes, authenticated_agent=self.agent_name, trusted_keys=self.trusted_keys, expected_audience=self.audience, seen_nonces=self.seen_nonces)
        return {"status": res.status, "reason": res.reason, "message": full, "row_hash": res.row_hash, "public_key": self.pub_hex}
