import json
import os
import matplotlib.pyplot as plt
import numpy as np

def generate_compression_chart():
    input_path = "data/arca_symbolic_benchmark.jsonl"
    
    if not os.path.exists(input_path):
        print(f"Error: No se encuentra el archivo en {input_path}")
        return

    domains = []
    raw_tokens_list = []
    symbolic_tokens_list = []

    # Leer datos del benchmark
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            record = json.loads(line)
            domains.append(record["domain"].replace("_", " ").title())
            raw_tokens_list.append(len(record["raw_prompt"].split())) # Aproximación de tokens/palabras o codificación directa
            symbolic_tokens_list.append(len(record["symbolic_prompt"].split()))

    # Configuración de la gráfica de barras agrupadas
    x = np.arange(len(domains))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    
    rects1 = ax.bar(x - width/2, raw_tokens_list, width, label='Tokens Naturales', color='#e74c3c')
    rects2 = ax.bar(x + width/2, symbolic_tokens_list, width, label='Tokens Simbólicos (HEKT-NOVA)', color='#2980b9')

    ax.set_ylabel('Cantidad de Tokens', fontsize=12, fontweight='bold')
    ax.set_title('Comparativa de Compresión de Tokens por Dominio - HEKT-NOVA', fontsize=14, fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(domains, rotation=15, ha='right', fontsize=10)
    ax.legend(fontsize=11)

    # Añadir etiquetas de valores sobre las barras
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height}',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

    autolabel(rects1)
    autolabel(rects2)

    fig.tight_layout()
    
    # Crear directorio de salida si no existe
    os.makedirs("assets", exist_ok=True)
    output_path = "assets/token_compression_comparison.png"
    
    plt.savefig(output_path, dpi=300)
    print(f"[OK] Gráfica generada y exportada con éxito en: {output_path}")

if __name__ == "__main__":
    generate_compression_chart()
