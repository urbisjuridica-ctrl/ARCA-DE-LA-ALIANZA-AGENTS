---
name: hekt-nova-notation
version: 2.3.2
description: Typed telegraphic header notation (Claim paired with Check traces) for agent audit contracts.
author: urbisjuridica-ctrl (ARCA-DE-LA-ALIANZA-AGENTS)
license: MIT
---

# HEKT-NOVA v2.3.2 — Falsifiable Claim Notation & Audit Contract

> **Core Rule:** A HEKT-NOVA header is a `Claim` (agent state), requiring pairing with an external execution trace (`Check`) via `reconciler_audit.py`.

## Architecture & Domains
- **Layers:** Claim Layer (header `key=val`) + Check Layer (external witness/proxy) + Witness Verdict (`MATCH`, `MISMATCH`, `INCONCLUSIVE` in `witness_ledger.jsonl`).
- **Key Domains:** `[H::AGT]` (Attribution), `[H::VER]` (Verification), `[H::AUD]` (Audit Link), `[H::ETH]` / `[H::LAW]` (Policy), `[H::ERR]` (Deviation), `[H::CMP]` (Context Metadata), `[H::END]` (Trace Closure).
- **All 27 Closed Namespaces:** Engineering/Audit (`[H::SYS]`, `[H::CYB]`, `[H::SOF]`, `[H::SEC]`, `[H::NET]`, `[H::MEM]`, `[H::LOG]`, `[H::AGT]`, `[H::SWM]`, `[H::API]`, `[H::DBX]`, `[H::OPT]`, `[H::VER]`, `[H::AUD]`, `[H::TRN]`, `[H::CMP]`, `[H::ERR]`, `[H::END]`) and Alignment/Hermeneutic Benchmark (`[H::ALN]`, `[H::SYM]`, `[H::ETH]`, `[H::LAW]`, `[H::EPI]`, `[H::ONT]`, `[H::HER]`, `[H::GNO]`, `[H::COG]`).

*Full technical specification and integration scripts can be found in the workspace configuration.*
