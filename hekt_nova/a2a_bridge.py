from typing import Any, Dict, List, Optional
from hekt_external_verifier import verify_message, VerificationResult, ALLOWED_DOMAINS, HIGH_TRUST_DOMAINS
from hekt_nova.__version__ import __version__

HEKT_A2A_MIME = "application/hekt-nova"
HEKT_A2A_EXTENSION_URI = "https://github.com"

def build_a2a_agent_card(name: str, description: str, url: str, agent_version: str = __version__, skills: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Construye una Agent Card compatible con A2A declarando la extensión opcional HEKT-NOVA v3.0.4."""
    return {
        "name": name,
        "description": description,
        "url": url,
        "version": agent_version,
        "capabilities": {
            "streaming": True,
            "pushNotifications": False,
            "extensions": [
                {
                    "uri": HEKT_A2A_EXTENSION_URI,
                    "description": f"HEKT-NOVA v{__version__} deterministic telegraph notation & Ed25519 Claim vs. Check verification",
                    "required": False,
                    "params": {
                        "version": __version__,
                        "supported_domains": sorted(ALLOWED_DOMAINS),
                        "high_trust_domains": sorted(HIGH_TRUST_DOMAINS),
                        "signature_alg": "Ed25519",
                        "hash_algorithm": "sha256",
                        "replay_window_seconds": 300,
                        "mime_type": HEKT_A2A_MIME,
                        "fallback": "text/plain",
                    },
                }
            ],
        },
        "skills": skills or [],
    }

def wrap_hekt_a2a_part(hekt_message: str, human_summary: Optional[str] = None) -> Dict[str, Any]:
    """Envuelve un mensaje firmado HEKT-NOVA en un Message A2A (Part principal application/hekt-nova + fallback legible opcional)."""
    parts: List[Dict[str, Any]] = [{"kind": "data", "mimeType": HEKT_A2A_MIME, "data": hekt_message}]
    if human_summary:
        parts.append({"kind": "text", "text": human_summary})
    return {"role": "agent", "parts": parts}

def verify_a2a_message(a2a_message: Dict[str, Any], trusted_keys: Optional[Dict[str, str]] = None, expected_audience: Optional[str] = None, seen_nonces: Optional[set] = None) -> VerificationResult:
    """Extrae el Part application/hekt-nova de una Task/Message A2A y aplica verify_message() en modo fail-closed."""
    parts = a2a_message.get("parts") if isinstance(a2a_message, dict) else None
    if not isinstance(parts, list) or not parts:
        return VerificationResult(status="REJECTED", reason="A2A_EMPTY_PARTS")
    hekt_parts = [p for p in parts if isinstance(p, dict) and p.get("mimeType") == HEKT_A2A_MIME]
    if not hekt_parts:
        return VerificationResult(status="REJECTED", reason="A2A_MISSING_HEKT_PART")
    if len(hekt_parts) > 1:
        return VerificationResult(status="REJECTED", reason="A2A_MULTIPLE_HEKT_PARTS")
    payload = hekt_parts[0].get("data")
    if not isinstance(payload, str):
        return VerificationResult(status="REJECTED", reason="A2A_INVALID_HEKT_PAYLOAD_TYPE")
    return verify_message(payload, trusted_keys=trusted_keys, expected_audience=expected_audience, seen_nonces=seen_nonces)
