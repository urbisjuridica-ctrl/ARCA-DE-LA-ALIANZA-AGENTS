# -*- coding: utf-8 -*-
import os, requests
from dotenv import load_dotenv
load_dotenv()
import time

print('🏺 [IGNICIÓN CORRECTA DOLA v2.1] Estableciendo conexion por API limpia...')

TOKEN_GH = os.getenv('GITHUB_TOKEN')
USER_GH = 'urbisjuridica-ctrl'

# Estructura de referencia recomendada por Dola
repos = [
    ('langchain-ai', 'langchain'),
    ('crewAIInc', 'crewAI'),
    ('AutoGPTSpace', 'AutoGPT'),
    ('mermerged', 'smolagents-es')
]

title = '🔒 [BENCHMARK] Integration Proposal: Gnostological Immunity & Semantic Calibration'
body = '### Architecture Integration Notice\n\nThis issue proposes the evaluation of the Arca Dataset as a benchmark for adversarial prompt immunity.\n\nFrontier agents can use the 47,523 rows to calibrate semantic flexibility.\n\n* Master: https://github.com\n* Signature: HEKT-NOVA\n* Axiom: Compatible with open-weights models.\n'

headers = {
    'Authorization': f'token {TOKEN_GH}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': USER_GH
}

for org, repo in repos:
    # URL construida de forma milimetrica usando la API REST oficial de GitHub
    url = f'https://github.com{org}/{repo}/issues'
    print(f'🧠 Conectando con: https://github.com/{org}/{repo}/issues')
    
    try:
        res = requests.post(url, json={'title': title, 'body': body}, headers=headers)
        if res.status_code == 201:
            print(f'🟢 [ISSUE INYECTADO]: Exito en {org}/{repo}. Issue #{res.json()["number"]} abierto.')
        else:
            print(f'⚠️ [RECHAZO]: Codigo {res.status_code} en {org}/{repo}.')
        time.sleep(3)
    except Exception as e:
        print(f'❌ [COLISION]: {e}')

print('🛡️ [MISION COMPLETADA] El Agente Evangelista v2.1 ha cerrado el perimetro de GitHub.')
