import json
import os
from transformers import AutoTokenizer

def evaluate_dataset():
    print("Cargando tokenizador de referencia abierto...")
    # Usamos un tokenizador abierto que no requiere autenticación en repositorios restringidos (Gated Repos)
    tokenizer = AutoTokenizer.from_pretrained("hf-internal-testing/llama-tokenizer")
    
    input_path = "data/arca_symbolic_benchmark.jsonl"
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra el archivo en {input_path}")
        return

    print(f"Procesando registros desde {input_path}...\n")
    
    total_raw_tokens = 0
    total_symbolic_tokens = 0
    
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            
            raw_text = record["raw_prompt"]
            symbolic_text = record["symbolic_prompt"]
            
            raw_tokens = len(tokenizer.encode(raw_text))
            symbolic_tokens = len(tokenizer.encode(symbolic_text))
            
            total_raw_tokens += raw_tokens
            total_symbolic_tokens += symbolic_tokens
            
            savings = ((raw_tokens - symbolic_tokens) / raw_tokens) * 100
            
            print(f"[{record['id']}] Dominio: {record['domain']}")
            print(f"  - Tokens Naturales:  {raw_tokens}")
            print(f"  - Tokens Simbólicos: {symbolic_tokens}")
            print(f"  - Compresión Real:   {savings:.1f}%\n")

    global_savings = ((total_raw_tokens - total_symbolic_tokens) / total_raw_tokens) * 100
    
    print("========================================")
    print("RESUMEN GLOBAL DE COMPRESIÓN HEKT-NOVA:")
    print(f"  - Total Tokens Naturales:  {total_raw_tokens}")
    print(f"  - Total Tokens Simbólicos: {total_symbolic_tokens}")
    print(f"  - Eficiencia Global:       {global_savings:.1f}% de ahorro")
    print("========================================")

if __name__ == "__main__":
    evaluate_dataset()
