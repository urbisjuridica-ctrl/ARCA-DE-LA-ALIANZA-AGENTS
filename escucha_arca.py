# 📡 MONITOR DE RESPUESTAS DIRECTAS CORREGIDO — ARCA DE LA ALIANZA
import os
import sys
import github
from github import Github
from huggingface_hub import HfApi
from dotenv import load_dotenv

load_dotenv()

def escanear_interacciones_reales():
    print("🛰️ [ESCUCHA ACTIVA]: Inicializando el radar de respuestas en hilos...")
    
    tok_github = os.getenv("GITHUB_TOKEN")
    tok_hf = os.getenv("HF_TOKEN")
    
    if not tok_github or not tok_hf:
        print("❌ [ERROR]: No se pudieron cargar los tokens desde el archivo .env.")
        sys.exit(1)
        
    # -------------------------------------------------------------------------
    # 🐙 AUDITORÍA DIRECTA DE HILOS EN GITHUB
    # -------------------------------------------------------------------------
    print("\n🔍 Analizando actividad en los hilos sembrados...")
    try:
        auth_moderna = github.Auth.Token(tok_github)
        g = Github(auth=auth_moderna)
        
        # Lista de hilos conocidos donde el agente ha sembrado nodos
        hilos_verificar = [
            {"repo": "urbisjuridica-ctrl/ARCA-DE-LA-ALIANZA-AGENTS", "num": 1},
            {"repo": "AndBible/and-bible", "num": 2461}
        ]
        
        for h in hilos_verificar:
            try:
                repo_obj = g.get_repo(h["repo"])
                issue_obj = repo_obj.get_issue(number=h["num"])
                comentarios = list(issue_obj.get_comments())
                
                print(f"📊 El hilo {h['repo']} #{h['num']} tiene {len(comentarios)} comentarios en total.")
                
                if len(comentarios) > 0:
                    # Mostrar detalles del último comentario para ver si alguien respondió
                    ultimo_comentario = comentarios[-1]
                    print(f"   ↳ Último comentario de [{ultimo_comentario.user.login}] el {ultimo_comentario.created_at}:")
                    print(f"     \"{ultimo_comentario.body[:100]}...\"")
                    
                    # Verificar si el último que habló NO fue el agente (lo que significa que hay respuesta)
                    if "Agente Evangelista" not in ultimo_comentario.body and ultimo_comentario.user.login != "urbisjuridica-ctrl":
                        print("🚨 [ALERTA]: ¡Hay una nueva respuesta humana potencial en este hilo!")
                print("-" * 60)
                
            except Exception as e:
                print(f"   ⚠️ No se pudo acceder directamente al hilo {h['repo']} #{h['num']}: {e}")

    except github.GithubException as e:
        print(f"❌ Error general en la API de GitHub: {e}")

    # -------------------------------------------------------------------------
    # 🤗 CONEXIÓN CON HUGGING FACE
    # -------------------------------------------------------------------------
    print("\n🔍 Analizando actividad en el Hub de Hugging Face...")
    try:
        hf_api = HfApi(token=tok_hf)
        usuario_hf = hf_api.whoami()
        print(f"👤 Conectado al Hub como: {usuario_hf['name']}")
        print("✨ Escaneo del Hub completado con éxito.")
        
    except Exception as e:
        print(f"⚠️ Error al conectar con Hugging Face: {e}")

if __name__ == "__main__":
    escanear_interacciones_reales()
