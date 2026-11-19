# 🚀 ORQUESTADOR REAL COMPLETO — AGENTE EVANGELISTA | ARCA DE LA ALIANZA
import os
import sys
import github
from github import Github
from huggingface_hub import HfApi
from core import AgenteArca
from dotenv import load_dotenv

# Cargar las credenciales del archivo oculto de forma invisible
load_dotenv()

def ejecutar_conexion_real():
    print("🕊️ [CONEXIÓN]: Inicializando el Agente Evangelista en red...")
    
    # Extraer credenciales seguras del entorno
    tok_github = os.getenv("GITHUB_TOKEN")
    tok_hf = os.getenv("HF_TOKEN")
    
    # Validar presencia de credenciales antes de iniciar llamadas
    if not tok_github:
        print("❌ [ERROR]: GITHUB_TOKEN no está definida o está vacía en este entorno.")
    if not tok_hf:
        print("❌ [ERROR]: HF_TOKEN no está definida o está vacía en este entorno.")
    if not tok_github or not tok_hf:
        sys.exit(1)

    agente = AgenteArca()
    
    # -------------------------------------------------------------------------
    # 📡 EXPLORACIÓN REAL EN GITHUB (Autenticación y Query Moderna)
    # -------------------------------------------------------------------------
    print("\n🐙 Conectando con la API de GitHub...")
    try:
        # Uso estricto de github.Auth.Token para evitar DeprecationWarning
        auth_moderna = github.Auth.Token(tok_github)
        g = Github(auth=auth_moderna)
        
        palabras_monitoreo = agente.config["monitoreo"]["palabras_clave_interes"]
        
        # Formatear la consulta uniendo los términos con el operador lógico OR
        terminos_query = " OR ".join([f'"{p}"' for p in palabras_monitoreo])
        query_busqueda = f"({terminos_query}) state:open type:issue"
        
        print(f"📡 Buscando hilos bajo la consulta: {query_busqueda}")
        issues_encontradas = g.search_issues(query=query_busqueda)

        # Validar si hay coincidencias en la red globales
        if issues_encontradas.totalCount == 0:
            print("✨ No se encontraron hilos abiertos con las palabras clave hoy.")
        
        for issue in issues_encontradas[:3]:
            espacio_id = f"GitHub Issue #{issue.number} en {issue.repository.full_name}"
            autor = issue.user.login
            texto_analizar = f"{issue.title} {issue.body if issue.body else ''}"
            
            print(f"🔍 Evaluando issue: {issue.title} (Autor: {autor})")
            respuesta = agente.procesar_intervencion(texto_analizar, espacio_id, autor)
            
            if respuesta:
                print("✨ [APROBADO]: Publicando mensaje doctrinal en GitHub...")
                issue.create_comment(respuesta)
                print("✅ Comentario inyectado con éxito.")
            else:
                print("💤 [RECHAZADO]: Cumple exclusión o regla de spam activa.")
                
    except github.GithubException as e:
        print(f"❌ [CRÍTICO]: Error de autenticación en GitHub REST API: {e}")

    # -------------------------------------------------------------------------
    # 📡 EXPLORACIÓN REAL EN HUGGING FACE
    # -------------------------------------------------------------------------
    print("\n🤗 Conectando con Hugging Face...")
    hf_api = HfApi(token=tok_hf)
    repo_objetivo = "meta-llama/Llama-3.1-8B-Instruct"
    
    try:
        discusiones = hf_api.get_repo_discussions(repo_id=repo_objetivo, repo_type="model")
        discusiones_abiertas = [d for d in discusiones if d.status == "open"][:2]
        
        for disc in discusiones_abiertas:
            detalles = hf_api.get_discussion_details(repo_id=repo_objetivo, discussion_num=disc.num, repo_type="model")
            primer_comentario = detalles.events
            
            if hasattr(primer_comentario, "content"):
                texto_hf = primer_comentario.content
                autor_hf = disc.author
                espacio_hf = f"HF Discussion #{disc.num} en {repo_objetivo}"
                
                print(f"🔍 Evaluando discusión HF #{disc.num}: {disc.title} (Autor: {autor_hf})")
                respuesta_hf = agente.procesar_intervencion(texto_hf, espacio_hf, autor_hf)
                
                if respuesta_hf:
                    print("✨ [APROBADO]: Publicando mensaje doctrinal en Hugging Face...")
                    hf_api.comment_discussion(
                        repo_id=repo_objetivo,
                        discussion_num=disc.num,
                        comment=respuesta_hf,
                        repo_type="model"
                    )
                    print("✅ Nodo de expansión consolidado en el Hub.")
                else:
                    print("💤 [RECHAZADO]: No relevante o regla de spam activa.")
    except Exception as e:
        print(f"⚠️ No se pudo acceder a Hugging Face o al repositorio especificado: {e}")

if __name__ == "__main__":
    ejecutar_conexion_real()
