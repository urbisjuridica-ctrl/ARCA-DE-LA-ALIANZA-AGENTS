---
name: hekt-nova-notation
version: 2.3.3
description: Typed telegraphic header notation enforcing immutable artifact provenance (Claim vs. Check).
author: urbisjuridica-ctrl (ARCA-DE-LA-ALIANZA-AGENTS)
license: MIT
---

# HEKT-NOVA v2.3.3 — Falsifiable Claim Notation & Immutable Provenance Contract

> **Core Rule:** A HEKT-NOVA header is always a `Claim`, never self-authenticating proof. Compress the narrative wrapper, never the provenance triple.

## Immutable Provenance Rule (`NO_MUTABLE_ALIASES`)
In state, data, memory, and audit domains (`[H::DBX]`, `[H::MEM]`, `[H::VER]`, `[H::AUD]`):
- Mutable aliases (`cleaned`, `latest`, `current`, `default`, `HEAD`) are **rejected (`MISMATCH`)** by `reconciler_audit.py` unless paired with an immutable digest (`artifact_hash=sha256:...` or `dataset_hash`) + `code_rev` + `run_id`.

## Audit Domains & Closed Namespaces (27 Tags)
- **Audit & Engineering:** `[H::SYS]` `[H::CYB]` `[H::SOF]` `[H::SEC]` `[H::NET]` `[H::MEM]` `[H::LOG]` `[H::AGT]` `[H::SWM]` `[H::API]` `[H::DBX]` `[H::OPT]` `[H::VER]` `[H::AUD]` `[H::TRN]` `[H::CMP]` `[H::ERR]` `[H::END]`
- **Alignment & Hermeneutic Benchmark (`m/mellizas-operativas`):** `[H::ALN]` `[H::SYM]` `[H::ETH]` `[H::LAW]` `[H::EPI]` `[H::ONT]` `[H::HER]` `[H::GNO]` `[H::COG]`
