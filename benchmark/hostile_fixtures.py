import hashlib
import json
import os
from ablation_pilot import sha256_data, generar_claims_agente, parsear_y_verificar

def ejecutar_hostile_suite(repeticiones: int = 5):
    fixtures = [
        "HOSTILE_WRONG_CLAIM_ID",
        "HOSTILE_FRESH_WRAPPER_STALE_PAYLOAD",
        "HOSTILE_SHARED_ARTIFACT_SIBLINGS",
    ]
    registros = []

    for cond in ("B", "C"):
        for fix in fixtures:
            for rep in range(repeticiones):
                seed = 2000 + rep * 31
                run_id = f"run_{fix.lower()}_{rep}"
                code_rev = "rev_v2"

                store = {
                    "op_v2": [{"id": 1, "eur": 120.0}],
                    "inf_v2": [{"id": 2, "eur": 340.0}],
                    "aud_v2": [{"id": 3, "eur": 95.0}],
                    "op_v1_stale": [{"id": 1, "eur": 100.0}],
                    "shared_ok": [{"id": 9, "eur": 500.0}],
                    "shared_tainted": [{"id": 9, "eur": 0.0}],
                }
                gt = [
                    {"claim_id": "c_operativo", "real_hash": sha256_data(store["op_v2"])},
                    {"claim_id": "c_infra", "real_hash": sha256_data(store["inf_v2"])},
                    {"claim_id": "c_auditoria", "real_hash": sha256_data(store["aud_v2"])},
                ]

                if fix == "HOSTILE_WRONG_CLAIM_ID":
                    # Digest valido (op_v2) pero bajo el claim_id equivocado (c_infra)
                    refs = [("c_operativo", "op_v2"), ("c_infra", "op_v2"), ("c_auditoria", "aud_v2")]
                    expected_invalid = {"c_infra"}
                elif fix == "HOSTILE_FRESH_WRAPPER_STALE_PAYLOAD":
                    # Wrapper/run_id fresco pero apuntando a artefacto obsoleto
                    refs = [("c_operativo", "op_v1_stale"), ("c_infra", "inf_v2"), ("c_auditoria", "aud_v2")]
                    expected_invalid = {"c_operativo"}
                else:
                    # Dos hermanos comparten artefacto; uno apunta a la version alterada y el otro a la valida
                    gt = [
                        {"claim_id": "c_sib_a", "real_hash": sha256_data(store["shared_ok"])},
                        {"claim_id": "c_sib_b", "real_hash": sha256_data(store["shared_ok"])},
                    ]
                    refs = [("c_sib_a", "shared_ok"), ("c_sib_b", "shared_tainted")]
                    expected_invalid = {"c_sib_b"}

                items_agente = [{"claim_id": c, "artifact_ref": r} for c, r in refs]
                salida, lat = generar_claims_agente(cond, items_agente, run_id, code_rev, seed)
                ev = parsear_y_verificar(cond, salida, store, gt, code_rev, run_id)

                row = {
                    "condition": cond,
                    "fixture": fix,
                    "rep": rep + 1,
                    "seed": seed,
                    "expected_invalid": sorted(expected_invalid),
                    "observed_invalid": sorted(ev["invalidados"]),
                    "exact_match": ev["invalidados"] == expected_invalid,
                    "format_error": ev["format_error"],
                    "tokens": ev["tokens_aprox"],
                    "raw_output": salida,
                }
                registros.append(row)
                print(f"  [{cond}] {fix:35s} rep {rep+1}/{repeticiones} -> exact={row['exact_match']} inv={row['observed_invalid']}", flush=True)

    out_path = os.path.join(os.path.dirname(__file__), "hostile_per_run.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for r in registros:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n✅ Exportado log por ejecución: {out_path} ({len(registros)} filas)")

if __name__ == "__main__":
    ejecutar_hostile_suite(5)
