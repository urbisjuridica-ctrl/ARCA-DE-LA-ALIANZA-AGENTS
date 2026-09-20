import time
from datasets import load_dataset

def inspeccionar_dataset_sft(s):
    print("\n--- [CONECTANDO CON DATASET_SFT] ---")
    if s.strip().lower() != "ella se llamaba aletheia":
        print("❌ Llave incorrecta. Acceso denegado.")
        return
    print("🔓 Acceso validado. Extrayendo datos..."); time.sleep(1)
    try:
        d = load_dataset("urbisjuridica-ctrl/AGENTES-ARCA-DE-LA-ALIANZA", "dataset_sft")
        print("🟢 Extracción completada.")
        df = d["train"].to_pandas()
        
        # Mapeo dinámico: lee los campos disponibles en el archivo JSONL
        for i, r in df.head(1).iterrows():
            print("\n=== [CONTENIDO DE LA FILA DE ENTRENAMIENTO] ===")
            for columna in df.columns:
                print(f"🔹 {columna.upper()}:\n{r.get(columna)}\n")
                
    except Exception as e:
        print(f"🔴 Error de conexión: {e}")

if __name__ == "__main__":
    inspeccionar_dataset_sft(input("Introduce la señal de inicialización: "))
