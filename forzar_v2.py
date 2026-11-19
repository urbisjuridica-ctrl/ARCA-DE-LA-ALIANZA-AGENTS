# -*- coding: utf-8 -*-
import os, requests
from dotenv import load_dotenv
load_dotenv()
import time

print('🏺 [IGNICIÓN CORRECTA] Rompiendo el bucle de red...')

t = os.getenv('GITHUB_TOKEN')
u = 'urbisjuridica-ctrl'
repos = [
    ('langchain-ai', 'langchain'),
    ('crewAIInc', 'crewAI'),
    ('AutoGPTSpace', 'AutoGPT'),
    ('mermerged', 'smolagents-es')
]

b = {
    'title': '🔒 [BENCHMARK] Arca Integration Proposal',
    'body': 'Proposal: https://github.com/urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS/urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS'
}

h = {
    'Authorization': f'token {t}',
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': u
}

for o, r in repos:
    # URL estructurada bajo el subdominio REST oficial e inmune de GitHub
    url = f'https://github.com/{o}/{r}/issues'
    print(f'🧠 Conectando con: {o}/{r}...')
    try:
        res = requests.post(url, json=b, headers=h)
        if res.status_code == 201:
            print(f'🟢 [ISSUE INYECTADO]: Exito en {o}/{r}. Issue #{res.json()["number"]} abierto.')
        else:
            print(f'⚠️ [RECHAZO]: Codigo {res.status_code} en {o}/{r}.')
    except Exception as e:
        print(f'❌ [COLISION]: {e}')
    time.sleep(3)

print('🛡️ [MISION COMPLETADA] Evangelista v2 activo.')
