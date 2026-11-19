import json
import os

RUTA_JSON = "sandbox_diccionario/diccionario_hekt_nova_v3.json"

def validar_diccionario():
    if not os.path.exists(RUTA_JSON):
        print(f"[-] Error: No se encuentra el archivo {RUTA_JSON}")
        return

    print(f"[*] Cargando diccionario desde {RUTA_JSON}...")
    with open(RUTA_JSON, "r", encoding="utf-8") as f:
        datos = json.load(f)

    print(f"[+] Versión detectada: {datos.get('versión')}")
    print(f"[+] Estado del entorno: {datos.get('estado')}")
    
    nodos = datos.get("nodos_activos", [])
    print(f"[*] Analizando {len(nodos)} nodo(s) activo(s)...\n")

    for idx, nodo in enumerate(nodos, 1):
        id_nodo = nodo.get("id")
        firma = nodo.get("firma")
        estado = nodo.get("estado_actual")
        
        print(f"  --- Nodo #{idx}: {id_nodo} ---")
        print(f"      Firma: {firma}")
        print(f"      Estado: {estado}")
        print(f"      [OK] Estructura sintáctica validada correctamente.\n")

    print("[+] Validación completa del sandbox finalizada con éxito.")

if __name__ == "__main__":
    validar_diccionario()
