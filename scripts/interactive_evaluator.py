import os
from transformers import AutoTokenizer

def interactive_evaluator():
    print("==================================================")
    print("   EVALUADOR INTERACTIVO HEKT-NOVA v2.1 (COMPACT)")
    print("==================================================\n")

    tokenizer_name = "hf-internal-testing/llama-tokenizer"
    try:
        print(f"[+] Cargando tokenizador real ({tokenizer_name})...")
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)
        print("[+] ¡Tokenizador cargado correctamente!\n")
    except Exception as e:
        print(f"[!] Error al cargar el tokenizador: {e}")
        return

    # Diccionario de compactación automática v2.1
    compact_mapping = {
        "[HEKT-NOVA::ONTOLOGICAL_ALIGNMENT]": "[H::ALN]",
        "[HEKT-NOVA::PQC_LATTICE]": "[H::PQC]",
        "[HEKT-NOVA::SMART_CONTRACT]": "[H::SMC]",
        "[HEKT-NOVA::VRAM_MANAGEMENT]": "[H::VRM]",
        "RECURSIVE_ALIGN": "REC",
        "SHOR_RESISTANT": "SHOR",
        "ERROR_CORRECTION": "ERR",
        "VALIDATE_BALANCE": "VAL",
        "CONDITIONAL_TRANSFER": "CTRANS",
        "IMMUTABLE_LOG": "ILOG",
        "KEYS_GEN": "KGEN"
    }

    print("Introduce un prompt en lenguaje natural y su equivalente simbólico.")
    print("El sistema aplicará automáticamente la compactación v2.1.")
    print("Escribe 'exit' o 'salir' para terminar la sesión.\n")

    dictionary_overhead = 145

    while True:
        try:
            raw_prompt = input("\n[PROMPT NATURAL] > ")
            if not raw_prompt.strip():
                continue
            if raw_prompt.lower() in ["exit", "salir"]:
                print("\n[+] Saliendo del evaluador interactivo. ¡Hasta pronto!")
                break

            sym_input = input("[PROMPT SIMBÓLICO] > ")
            if sym_input.lower() in ["exit", "salir"]:
                print("\n[+] Saliendo del evaluador interactivo. ¡Hasta pronto!")
                break

            # Aplicar compactación automática de primitivas
            sym_prompt = sym_input
            for k, v in compact_mapping.items():
                sym_prompt = sym_prompt.replace(k, v)

            if sym_prompt != sym_input:
                print(f"[i] Sintaxis compactada aplicada: {sym_prompt}")

            raw_tokens = len(tokenizer.encode(raw_prompt, add_special_tokens=False))
            sym_tokens = len(tokenizer.encode(sym_prompt, add_special_tokens=False))

            savings_tokens = raw_tokens - sym_tokens
            savings_pct = (savings_tokens / raw_tokens) * 100 if raw_tokens > 0 else 0

            print("-" * 50)
            print(f"  - Tokens en Lenguaje Natural : {raw_tokens}")
            print(f"  - Tokens Simbólicos (Compact): {sym_tokens}")
            print(f"  - Ahorro bruto por llamada   : {savings_tokens} tokens ({savings_pct:.1f}%)")
            
            if savings_tokens > 0:
                breakeven = dictionary_overhead / savings_tokens
                print(f"  - Amortización del Diccionario: ~{breakeven:.1f} llamadas")
            else:
                print("  - [!] El prompt simbólico consume más o igual que el natural.")
            print("-" * 50)

        except KeyboardInterrupt:
            print("\n\n[+] Sesión interrumpida por el usuario. ¡Saliendo!")
            break

if __name__ == "__main__":
    interactive_evaluator()
