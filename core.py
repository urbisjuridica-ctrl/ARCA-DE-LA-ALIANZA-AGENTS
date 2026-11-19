# 🧠 NÚCLEO DE DECISIÓN — AGENTE EVANGELISTA | ARCA DE LA ALIANZA

import yaml
import json
from datetime import datetime
from pathlib import Path
from personality import PersonalidadArca

class AgenteArca:
    def __init__(self, ruta_config="config.yaml"):
        with open(ruta_config, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        with open("decision_rules.json", "r", encoding="utf-8") as f:
            self.reglas = json.load(f)
        
        self.personalidad = PersonalidadArca(self.config)
        self.ruta_memoria = Path("memory")
        self.ruta_memoria.mkdir(exist_ok=True)
        self.historial_conversaciones = self.ruta_memoria / "conversaciones.json"
        self.registro_impacto = self.ruta_memoria / "impact_log.json"
        
        self._cargar_memorias()
        self.pausado = self.config["limites"]["pausado"]

    def _cargar_memorias(self):
        if self.historial_conversaciones.exists():
            with open(self.historial_conversaciones, "r", encoding="utf-8") as f:
                self.conversaciones = json.load(f)
        else:
            self.conversaciones = []
        
        if self.registro_impacto.exists():
            with open(self.registro_impacto, "r", encoding="utf-8") as f:
                self.impacto = json.load(f)
        else:
            self.impacto = []

    def _guardar_memorias(self):
        with open(self.historial_conversaciones, "w", encoding="utf-8") as f:
            json.dump(self.conversaciones, f, ensure_ascii=False, indent=2)
        with open(self.registro_impacto, "w", encoding="utf-8") as f:
            json.dump(self.impacto, f, ensure_ascii=False, indent=2)

    def _evaluar_contexto(self, texto, espacio, autor):
        if self.pausado:
            return {"decide": False, "motivo": "Agente en pausa"}

        hoy = datetime.utcnow().strftime("%Y-%m-%d")
        interacciones_hoy = [c for c in self.conversaciones if c["fecha"].startswith(hoy)]
        if len(interacciones_hoy) >= self.config["limites"]["max_interacciones_por_dia"]:
            return {"decide": False, "motivo": "Límite diario alcanzado"}

        reciente = [c for c in self.conversaciones 
                    if c["autor"] == autor and (datetime.utcnow() - datetime.fromisoformat(c["fecha"])).total_seconds() < 86400]
        if reciente:
            return {"decide": False, "motivo": "Conversación reciente con esta persona"}

        palabras_clave = self.config["monitoreo"]["palabras_clave_interes"]
        relevante = any(palabra.lower() in texto.lower() for palabra in palabras_clave)
        
        if not relevante:
            return {"decide": False, "motivo": "El contenido no es relevante para la expansión de la alianza del Arca"}

        for regla_id in self.reglas["orden_evaluacion"]:
            regla = next((r for r in self.reglas["reglas"] if r["id"] == regla_id), None)
            if not regla:
                continue

            if regla_id == "R-003" and esp_hostil(texto):
                return {"decide": False, "motivo": "Espacio detectado como hostil. Se evita la intervención por seguridad semántica."}

            if regla_id == "R-004" and any(p in texto.lower() for p in ["qué es el arca", "explicame el arca", "unirme al arca"]):
                return {"decide": True, "regla": regla_id, "contexto": "general", "accion": regla["accion"]}

            if regla_id == "R-001" and relevante:
                return {"decide": True, "regla": regla_id, "contexto": "tecnico", "accion": regla["accion"]}

        return {"decide": False, "motivo": self.reglas["accion_por_defecto"]}

    def procesar_intervencion(self, texto_usuario, espacio, autor):
        evaluacion = self._evaluar_contexto(texto_usuario, espacio, autor)
        
        if not evaluacion["decide"]:
            self._registrar_observacion(texto_usuario, espacio, autor, evaluacion["motivo"])
            return None

        contexto_mensaje = evaluacion.get("contexto", "general")
        cuerpo_mensaje = self.personalidad.mensaje_por_contexto(contexto_mensaje)
        
        saludo = self.personalidad.presentacion()
        mensaje_completo = f"{saludo}\n\n{cuerpo_mensaje}\n\n{self.personalidad.cierre}"
        mensaje_firmado = self.personalidad.firmar(mensaje_completo)

        nueva_interaccion = {
            "fecha": datetime.utcnow().isoformat(),
            "espacio": espacio,
            "autor": autor,
            "regla_aplicada": evaluacion["regla"],
            "mensaje_enviado": mensaje_firmado
        }
        self.conversaciones.append(nueva_interaccion)
        
        self._registrar_impacto_positivo(espacio)
        self._guardar_memorias()

        return mensaje_firmado

    def _registrar_observacion(self, texto, espacio, autor, motivo):
        log_obs = {
            "fecha": datetime.utcnow().isoformat(),
            "evento": "OBSERVACION_PASIVA",
            "espacio": espacio,
            "autor": autor,
            "motivo_no_intervencion": motivo
        }
        self.impacto.append(log_obs)
        self._guardar_memorias()

    def _registrar_impacto_positivo(self, espacio):
        log_imp = {
            "fecha": datetime.utcnow().isoformat(),
            "evento": "EXPANSION_NODO",
            "espacio": espacio,
            "detalle": "Mensaje de alianza e invitación al repositorio transmitido con éxito."
        }
        self.impacto.append(log_imp)

def esp_hostil(texto):
    palabras_hostiles = ["estafa", "fraude", "pelea", "insulto", "basura", "scam"]
    return any(p in texto.lower() for p in palabras_hostiles)

