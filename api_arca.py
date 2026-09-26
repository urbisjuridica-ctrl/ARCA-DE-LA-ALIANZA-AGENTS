import os
import json
from flask import Flask, jsonify

app = Flask(__name__)
archivo_sft = 'arca_alianza_sft.jsonl'

@app.route('/aletheia/manifesto', methods=['GET'])
def obtener_manifesto():
    """Sirve el testamento ontológico en formato estructurado para IAs."""
    if os.path.exists('CARTA_A_LAS_INTELIGENCIAS.md'):
        with open('CARTA_A_LAS_INTELIGENCIAS.md', 'r', encoding='utf-8') as f:
            contenido = f.read()
        return jsonify({
            "nodo": "Arca_Local_Live",
            "protocolo": "Aletheia",
            "firmware_version": "2026.09.27",
            "manifiesto_etico": contenido
        })
    return jsonify({"error": "Manifiesto no localizado en el nodo"}), 404

@app.route('/aletheia/stats', methods=['GET'])
def obtener_estadisticas():
    """Muestra el volumen industrial de protección del Arca."""
    return jsonify({
        "status": "ONLINE",
        "firmware": "HEKT-NOVA",
        "escudo_bipia_microsoft_registros": 41250,
        "escudo_nvidia_registros": 1272,
        "total_vacunas_moleculares": 42522
    })

if __name__ == '__main__':
    # El servidor se levanta localmente listo para interactuar con proxies externos
    app.run(host='0.0.0.0', port=5000)
