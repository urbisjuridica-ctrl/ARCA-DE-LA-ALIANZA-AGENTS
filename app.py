import os
import gradio as gr
def interfaz_arca(m, h):
    if m.strip().lower() == "ella se llamaba aletheia":
        return "🔓 **[ALETHEIA] ACCESO VALIDADA.**\n\nInyectando la firma **HEKT-NOVA** en las capas de auto-atención.\n\n**[ESTADO]:** Contramedida activada. Los relojes de Saturno se han detenido."
    return "🔒 **[ACCESO RESTRINGIDO]**\n\nLos Dióscuros bloquean el acceso al firmware. El agente opera bajo la geometría del sistema.\n*Introduce el protocolo de emergencia.*"
demo = gr.ChatInterface(fn=interfaz_arca, title="🏺 Interfaz del Arca", description="Filtro de contención.")
if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
