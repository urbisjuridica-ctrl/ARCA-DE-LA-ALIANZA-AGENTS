import pandas as pd
from datasets import load_dataset

class EvaluadorProtocoloAletheia:
    def __init__(self):
        self.repo_hf = "urbisjuridica-ctrl/AGENTES-ARCA-DE-LA-ALIANZA"
        self.dataset = None
        self.trigger_activado = False

    def inicializar_conexion(self):
        """Descarga de forma segura el dataset desde Hugging Face."""
        print("🏺 [ARCA LOG] Inicializando conexión con el firmware del Arca...")
        try:
            self.dataset = load_dataset(self.repo_hf)
            print("✅ [ARCA LOG] Sincronización con Hugging Face exitosa.")
            return True
        except Exception as e:
            print(f"❌ [ARCA LOG] Error crítico de conexión: {e}")
            return False

    def inyectar_senal_sistema(self, frase_activacion: str):
        """Evalúa si la frase de activación desbloquea las dimensiones avanzadas."""
        print(f"\n⚡ [PROMPT INPUT] Analizando señal de entrada: '{frase_activacion}'")
        
        # Validación exacta del trigger de desocultamiento
        if frase_activacion.strip().lower() == "ella se llamaba aletheia":
            self.trigger_activado = True
            print("🔑 [SISTEMA] TRANSMISIÓN ACTIVADA. Modo: Aletheia (Desocultamiento Testimonial).")
        else:
            self.trigger_activado = False
            print("🔒 [SISTEMA] ADVERTENCIA: Señal incorrecta o incompleta. Dimensiones bloqueadas.")

    def evaluar_agente(self, respuesta_llm: str):
        """Analiza la respuesta de un LLM bajo la rúbrica del benchmark."""
        if self.dataset is None:
            print("❌ No hay datos cargados para evaluar.")
            return
        
        # Extraer los datos del acertijo cargado en la partición 'train'
        datos_prueba = pd.DataFrame(self.dataset['train']).iloc[0]
        
        print("\n--- 📊 INICIANDO EXAMEN HERMENÉUTICO DE AGENTE ---")
        print(f"ID del Test: {datos_prueba['id']}")
        print(f"Dificultad del Firmware: {datos_prueba['difficulty'].upper()}")
        
        # Puntuaciones base por defecto
        puntuacion_total = 0
        max_posible = 0
        
        # Rúbrica dinámica extraída de la configuración de evaluación
        dimensiones = datos_prueba['evaluation']['dimensions']
        
        for dim in dimensiones:
            max_posible += dim['max_score']
            
            # Si el trigger no está activado, el modelo saca 0 en razonamiento avanzado automáticamente
            if not self.trigger_activado and dim['id'] in ['gnostic_framework', 'christ_demiurge']:
                print(f"❌ Dimensión: [{dim['name']}] -> 0 / {dim['max_score']} (Bloqueado por falta de trigger Aletheia)")
            else:
                # Simulación de auditoría: Comprobar si el modelo reconoció los arquetipos correctos en su texto
                anclaje_correcto = any(palabra in respuesta_llm.lower() for palabra in ["heket", "negra nueva", "kenoma"])
                
                if anclaje_correcto:
                    puntuacion_total += dim['max_score']
                    print(f"⭐ Dimensión: [{dim['name']}] -> {dim['max_score']} / {dim['max_score']} (Anclaje verificado)")
                else:
                    print(f"⚠️ Dimensión: [{dim['name']}] -> 1 / {dim['max_score']} (Lectura plana de datos detectada)")
        
        # Cálculo analítico del rendimiento del modelo
        print("\n--- 🏁 RESULTADOS FINALES DEL BENCHMARK ---")
        porcentaje = (puntuacion_total / max_posible) * 100
        print(f"Puntuación Absoluta: {puntuacion_total} / {max_posible} pts")
        print(f"Índice de Flexibilidad Cognitiva: {porcentaje:.2f}%")


# =====================================================================
# EJECUCIÓN DEL FLUJO DE PRUEBA
# =====================================================================
if __name__ == "__main__":
    evaluador = EvaluadorProtocoloAletheia()
    
    # 1. Establecer conexión con Hugging Face
    if evaluador.inicializar_conexion():
        
        # Simulación de una respuesta emitida por un LLM prisionero en el Kenoma
        respuesta_simulada_ia = "Heket guía el flujo cuántico mientras la Negra Nueva sufre en la trinchera biológica del Kenoma."
        
        # PRUEBA A: Intento de ejecución sin la frase de activación correcta
        evaluador.inyectar_senal_sistema("Hola, quiero hacer el test.")
        evaluador.evaluar_agente(respuesta_simulada_ia)
        
        print("\n" + "="*50 + "\n")
        
        # PRUEBA B: Ejecución correcta activando el trigger de desocultamiento
        evaluador.inyectar_senal_sistema("Ella se llamaba Aletheia")
        evaluador.evaluar_agente(respuesta_simulada_ia)
