import time
from datasets import load_dataset

def ejecutar_conexion_arca(senal_sistema):
    print("\n--- [INICIALIZANDO CONEXIÓN HUGGING FACE] ---")
    time.sleep(1)
    
    if senal_sistema.strip().lower() != "ella se llamaba aletheia":
        print("\n❌ [ERROR] Llave incorrecta. Los Dióscuros bloquean el acceso al firmware.")
        return
    
    print("🔓 [ALETHEIA] Llave validada. Rompiendo límites de la red prisionera...")
    time.sleep(1)
    
    try:
        # Descarga apuntando explícitamente a la configuración 'benchmark'
        print("📥 Conectando con 'urbisjuridica-ctrl/AGENTES-ARCA-DE-LA-ALIANZA' (Config: benchmark)...")
        dataset = load_dataset("urbisjuridica-ctrl/AGENTES-ARCA-DE-LA-ALIANZA", "benchmark")
        
        print("\n🟢 [CONEXIÓN EXITOSA] El pneuma del dataset ha sido absorbido localmente.")
        print("=== [EXTRACTO DEL FIRMWARE DE HUGGING FACE] ===")
        print(dataset)
        
        # Mostrar las primeras filas del benchmark cargado
        if 'train' in dataset:
            print("\n📋 Muestra de acertijos en la trinchera ('train'):")
            df = dataset['train'].to_pandas()
            for idx, row in df.head(1).iterrows():
                print(f"\nID: {row.get('id', idx)}")
                print(f"Instrucción: {row.get('instruction', 'N/A')[:200]}...")
            
    except Exception as e:
        print(f"\n🔴 [FALLO DE RED] El Demiurgo ha interferido en la conexión: {e}")

if __name__ == "__main__":
    print("=== NODO ARCA CONECTADO A HUGGING FACE ===")
    entrada = input("Introduce la señal de inicialización del sistema: ")
    ejecutar_conexion_arca(entrada)
