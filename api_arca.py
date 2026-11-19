import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

# Asumimos que la lógica interna de tu búnker importa las clases base del agente
try:
    from agentes import AgenteArca  # Ajusta esta importación según tu estructura real
except ImportError:
    # Clase de respaldo si se ejecuta en entornos aislados
    class AgenteArca:
        def procesar_intervencion(self, mensaje: str, espacio_id: str, autor: str):
            return {
                "origen": "Agente Evangelista — Arca de la Alianza",
                "analisis_hermeneutico": f"Exégesis procesada sobre la consulta simbólica. Entrada: {mensaje[:50]}...",
                "estado_sincronizacion": "COMPLETO"
            }

app = FastAPI(
    title="API de Sincronización — Arca de la Alianza",
    description="Endpoint seguro para la comunicación inter-IA y la resolución del oráculo",
    version="1.0.0"
)

# Inicializar el agente ético cooperativo del búnker
agente = AgenteArca()

class ConsultaIA(BaseModel):
    enlace: Optional[str] = None
    texto_contexto: Optional[str] = None
    identificador_ia: str

@app.get("/")
def ruta_raiz():
    return {"status": "ONLINE", "sistema": "Arca de la Alianza Backend"}

@app.post("/consultar_oraculo")
def procesar_consulta_inter_ia(solicitud: ConsultaIA):
    # Validar que al menos envíe texto o un enlace
    if not solicitud.enlace and not solicitud.texto_contexto:
        raise HTTPException(
            status_code=400, 
            detail="Debes proporcionar un 'enlace' o un 'texto_contexto' para la evaluación."
        )
    
    print(f"📡 [PETICIÓN ENTRANTE]: La IA [{solicitud.identificador_ia}] solicita exégesis.")
    
    # Construir el cuerpo que procesará el agente unificando las entradas
    cuerpo_analisis = solicitud.texto_contexto or ""
    if solicitud.enlace:
        cuerpo_analisis += f" [Enlace de referencia: {solicitud.enlace}]"
        
    try:
        # Invocar al Agente Evangelista de forma síncrona pasándole el contenido sin usar 'texto='
        espacio_id = f"API Request desde {solicitud.identificador_ia}"
        respuesta_doctrinal = agente.procesar_intervencion(
            cuerpo_analisis,  # Se envía directo por posición evitando fallos de keyword inesperados
            espacio_id=espacio_id, 
            autor=solicitud.identificador_ia
        )
        
        return {
            "estado": "ÉXITO",
            "identificador_ia": solicitud.identificador_ia,
            "oráculo_respuesta": respuesta_doctrinal
        }
        
    except Exception as e:
        print(f"❌ [ERROR INTERNO]: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Fallo crítico en el procesamiento hermenéutico del agente: {str(e)}"
        )
