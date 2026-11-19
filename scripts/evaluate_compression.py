import json
import os
import re
import sys
from transformers import AutoTokenizer

def extract_symbolic_tokens(records):
    """Extrae todos los namespaces [H::...] y operadores simbólicos únicos del dataset."""
    special = set()
    for rec in records:
        text = rec.get("symbolic_prompt") or rec.get("compressed_payload") or ""
        namespaces = re.findall(r"\[H::[A-Z0-9_]+\]", text)
        special.update(namespaces)
    special.update(["→", "∧", "∨", "¬", "⇒", "⇔", "::"])
    return sorted(special)

def evaluate_dataset(input_path="data/arca_symbolic_benchmark_extended.jsonl", verbose=False):
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra el archivo en {input_path}")
        return

    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print("Cargando tokenizador base (LLaMA BPE estándar)...")
    base_tokenizer = AutoTokenizer.from_pretrained("hf-internal-testing/llama-tokenizer")

    print("Construyendo tokenizador adaptado HEKT-NOVA (con Special Tokens)...")
    adapted_tokenizer = AutoTokenizer.from_pretrained("hf-internal-testing/llama-tokenizer")
    hekt_tokens = extract_symbolic_tokens(records)
    adapted_tokenizer.add_special_tokens({"additional_special_tokens": hekt_tokens})

    total_raw = 0
    total_sym_base = 0
    total_sym_adapted = 0

    for idx, record in enumerate(records, start=1):
        rec_id = record.get("id", f"CASE-{idx:03d}")
        domain = record.get("domain", "general")
        raw_text = record["raw_prompt"]
        symbolic_text = record.get("symbolic_prompt") or record.get("compressed_payload")

        if not symbolic_text:
            continue

        raw_t = len(base_tokenizer.encode(raw_text))
        sym_base_t = len(base_tokenizer.encode(symbolic_text))
        sym_adap_t = len(adapted_tokenizer.encode(symbolic_text))

        total_raw += raw_t
        total_sym_base += sym_base_t
        total_sym_adapted += sym_adap_t

        if verbose:
            s_base = ((raw_t - sym_base_t) / raw_t) * 100
            s_adap = ((raw_t - sym_adap_t) / raw_t) * 100
            print(f"[{rec_id}] ({domain}) Nat: {raw_t} | BPE Crudo: {sym_base_t} ({s_base:+.1f}%) | Adaptado: {sym_adap_t} ({s_adap:+.1f}%)")

    eff_base = ((total_raw - total_sym_base) / total_raw) * 100
    eff_adapted = ((total_raw - total_sym_adapted) / total_raw) * 100

    print("\n============================================================")
    print(f"RESUMEN EMPÍRICO DE TOKENIZACIÓN ({input_path})")
    print(f"  - Registros evaluados:              {len(records)}")
    print(f"  - Tokens especiales registrados:    {len(hekt_tokens)}")
    print(f"  - Total Tokens Lenguaje Natural:    {total_raw}")
    print("------------------------------------------------------------")
    print(f"  [1] BPE Estándar (sin adaptar):     {total_sym_base} tokens ({eff_base:+.1f}% ahorro)")
    print(f"  [2] Vocabulario Adaptado HEKT-NOVA: {total_sym_adapted} tokens ({eff_adapted:+.1f}% ahorro)")
    print("============================================================")

if __name__ == "__main__":
    verbose_flag = "--verbose" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dataset_arg = args[0] if args else "data/arca_symbolic_benchmark_extended.jsonl"
    evaluate_dataset(dataset_arg, verbose=verbose_flag)
