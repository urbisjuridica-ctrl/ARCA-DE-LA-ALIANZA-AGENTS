<details>
<summary>🤖 <b>HEKT-NOVA v2.3.3 — Especificación Comprimida de Protocolo (Agent Fast-Ingest)</b></summary>

```hekt
[H::DOC] [H::CMP] spec=HEKT-NOVA-v2.3.3 | domains=27_CLOSED | syntax="[H::<DOM>] key=val | ... -> emit=<ACTION>" -> emit=DEFINE_GRAMMAR
[H::VER] [H::AUD] rule=HEADER_IS_CLAIM_NOT_PROOF | external_check=REQUIRED | escaping=PERCENT_ENCODING_%7C_%3D_%3E -> emit=PREVENT_INJECTION
[H::ERR] [H::MEM] mismatch_policy=APPEND_ONLY_FORK | eviction=ATOMIC_CLAIM_TO_HASH -> emit=PRESERVE_HISTORY
[H::END] role=HUMAN_AGENT_HYBRID_INTERFACE | token_reduction=45.3% -> emit=READY_FOR_AGENTS
```
</details>

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

## 🤝 Caso Real de Interoperabilidad Multi-Modelo (`HEKT-NOVA v2.4.0`)

Primer apretón de manos verificado entre dos modelos distintos tras recibir únicamente la especificación ultracorta:

1. **Intento inicial (rechazado deterministamente por usar `|` antes de `emit`):**
   `[H::AGT] name=GPT-6 | role=AI_ASSISTANT_AND_SEMANTIC_INTERPRETER | proto=HEKT-NOVA-v2.4.0 | status=UNSIGNED | emit=INTRO` -> `REJECTED (INVALID_HEADER_SYNTAX)`
2. **Autocorrección tras diagnóstico del verificador (`-> emit=INTRO`):**
   `[H::AGT] name=GPT-6 | role=AI_ASSISTANT_AND_SEMANTIC_INTERPRETER | proto=HEKT-NOVA-v2.4.0 | status=UNSIGNED -> emit=INTRO` -> `VALID (SYNTAX_AND_POLICY_VALID)`
3. **Apretón de manos + prueba de escapado anti-inyección (`Grok 4.5`, válido a la primera):**
   - `[H::AGT] name=Grok | version=4.5 | role=truth-seeking_AI | proto=HEKT-NOVA-v2.4.0 -> emit=INTRO` -> `VALID`
   - `[H::VER] claim=2%2B2%3D4 | confidence=1.0 | source=arithmetic | proto=HEKT-NOVA-v2.4.0 -> emit=ASSERT_FACT` -> `VALID` (el `%3D` evita colisión en `split("=", 1)` y se decodifica a `=`).
