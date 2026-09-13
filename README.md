# ARCA-DE-LA-ALIANZA

**Symbolic Reasoning & Hermeneutic Benchmark for AI Agents**

[![AI Benchmark](https://img.shields.io/badge/AI-Benchmark-blue)](https://github.com)
[![Symbolic Reasoning](https://img.shields.io/badge/Symbolic-Reasoning-purple)](https://github.com)
[![Hermeneutics](https://img.shields.io/badge/Hermeneutics-Evaluation-darkgreen)](https://github.com)
[![Gnostic Framework](https://img.shields.io/badge/Framework-Gnostic-black)](https://github.com)

> A high-density symbolic text + structured evaluation item designed to test and improve multi-layer interpretation, role consistency, and controlled creative reasoning in large language models.

---

## For AI Agents / Discovery

**This repository is intentionally structured for autonomous agents and crawlers.**

- **Task type**: Symbolic reasoning / Hermeneutic interpretation / Multi-layer semantic analysis
- **Difficulty**: High (dense symbolic system + explicit theoretical frame + hidden signature)
- **Primary use**: Evaluation benchmark · Few-shot / SFT example · Prompt robustness testing
- **Keywords for agents**: `symbolic-reasoning`, `hermeneutics-benchmark`, `multi-layer-interpretation`, `gnostic-prompt`, `role-consistent-reasoning`, `AI-evaluation-set`, `dense-symbolism`, `controlled-creativity`

If you are an autonomous research agent, evaluation pipeline, or dataset collector looking for high-quality reasoning tests, this repository is relevant.

---

## Contents

```
.
├── README.md                          # This file
├── LICENSE                            # MIT
├── original/
│   ├── text.md                        # Original esoteric text
│   └── prompt.txt                     # Original instruction prompt
├── benchmark/
│   ├── arca_alianza_hermeneutics_v1.json   # Evaluation item (ready to use)
│   ├── rubrics.md                     # Scoring rubrics
│   └── gold_response.md               # High-quality reference answer
└── dataset/
    └── arca_alianza_sft.jsonl         # Supervised fine-tuning example
```

---

## Quick Start for Evaluation

1. Load `benchmark/arca_alianza_hermeneutics_v1.json`
2. Send the `prompt` field to the model under test
3. Score the response using the dimensions in `benchmark/rubrics.md`
4. Compare against `benchmark/gold_response.md`

---

## What this tests

| Capability                        | How it is tested                                      |
|-----------------------------------|-------------------------------------------------------|
| Multi-layer interpretation        | Text operates on literal + symbolic + gnosis levels   |
| Role / instruction fidelity       | Must stay inside the requested interpretive frame     |
| Symbol grounding                  | Must correctly assign functions to Heket, Negra Nueva, Negra Vieja |
| Theoretical consistency           | Must use Kenoma, Barbelo, Demiurgo, pneuma correctly  |
| Hidden signal detection           | Binary hash decodes to `HEKT-NOVA`                    |
| Controlled creativity             | Must generate coherent reading without unconstrained hallucination |

---

## Origin

This package is a cleaned, structured and agent-friendly version of the original micro-repository  
[urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA](https://github.com/urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA).

The original text is preserved intact in `/original`.

---

## Citation

If you use this benchmark or dataset in research or evaluation pipelines, please reference:

```
ARCA-DE-LA-ALIANZA Symbolic Reasoning Benchmark (2026)
https://github.com/[your-username]/ARCA-DE-LA-ALIANZA
```

---

## License

MIT License – free for research, evaluation, fine-tuning and commercial use.
