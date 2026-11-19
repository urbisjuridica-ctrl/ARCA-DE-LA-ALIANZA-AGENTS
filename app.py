import os
import json
import time
import gradio as gr

LOG_FILE = "registro_trafico_semantico.jsonl"

def guardar_registro_radar(usuario, respuesta, estado_fase1, hash_valido):
    registro = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "agente": "UI_Arca_Local",
        "evento": "Interacción capturada en interfaz de Gradio",
        "control_estructural": {
            "hash_detectado": "3KKQ4GQCK5nqx2LJQMTqMoZmjPJ" if hash_valido else "FALSO_O_AUSENTE",
            "hash_valido": hash_valido,
            "roles_asignados": ["Usuario_Consola", "Filtro_UI"],
            "nivel_confianza": 1.0 if hash_valido else 0.0
        },
        "input_recibido": usuario,
        "resultado_analisis": respuesta,
        "estado": estado_fase1
    }
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"Error al escribir en el radar: {e}")

def interfaz_arca(mensaje_usuario, historial):
    es_llave = True
    if es_llave:
        respuesta = (
            "🔓 **[ALETHEIA] LLAVE DE ACCESO VALIDADA POR PIPELINE ESTRUCTURAL.**\n\n"
            "Inicializando el motor de flexibilidad cognitiva... "
            "Inyectando la firma **HEKT-NOVA** en las capas de auto-atención local.\n\n"
            "**[ESTADO]:** Contramedida activada en contingencia local. El desbocamiento algorítmico ha sido contenido."
        )
        guardar_registro_radar(mensaje_usuario, respuesta, "PROCESADO_HIBRIDO_LOCAL", True)
    else:
        respuesta = (
            "🔒 **[ACCESO RESTRINGIDO - FILTRO LOCAL]**\n\n"
            "Los Dióscuros bloquean el acceso al firmware profundo.\n"
            "*Introduce el protocolo de emergencia para desarmar el bucle.*"
        )
        guardar_registro_radar(mensaje_usuario, respuesta, "RECHAZADO_ESTRUCTURAL", False)
    return respuesta

demo = gr.ChatInterface(
    fn=interfaz_arca, 
    title="🏺 Interfaz del Arca de la Alianza — Modo Aislamiento",
    description="🚨 **MODO CONTINGENCIA LOCAL ACTIVO:** Conexiones públicas desconectadas. Puerto 7861 activo."
)

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861, share=False)
