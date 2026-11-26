# Security Policy & Threat Model — HEKT-NOVA v3.0.4

## Supported Versions

| Version | Status | Notes |
| :--- | :--- | :--- |
| `v3.0.4` | **Supported (Canonical)** | Ed25519 subgroup checks, `±300s` `ts` window, SQLite WAL `900s` nonce store, Python + TS/Node CI |
| `< v3.0.0` | Unsupported | Superseded legacy drafts |

## Threat Model & Trust Boundaries
1. **What `verify_message()` guarantees:** Deterministic syntax/policy enforcement (`SPEC_v3_0_0.md`), `Ed25519` header authenticity (`VALID`), `±300s` replay window, atomic nonce uniqueness (`SqliteNonceStore`), and `SHA-256` body binding.
2. **What it does NOT guarantee:** A signed `VALID` header proves *who* signed the claim and that the body hash matches—it does **not** prove the truthfulness of external facts unless corroborated by an independent `Check` harness outside the acting LLM's control.
3. **Operational Key & Host Separation:** Private keys (`HEKT_PRIVATE_KEY_FILE`, mode `0600`) must reside outside the repository and separate from the verifier's `trusted_keys` registry.

## Single-Command Reproducibility
```bash
pytest -v && (cd packages/hekt-nova-ts && npm test)
```

## Reporting a Vulnerability
Please report security issues privately via GitHub Security Advisories (`urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS/security/advisories/new`).
