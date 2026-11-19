import os
from huggingface_hub import HfApi

def publish_to_huggingface():
    repo_id = "urbisjuridica-ctrl/arca-symbolic-token-bench"
    repo_type = "dataset"
    
    api = HfApi()
    
    print(f"Conectando con Hugging Face Hub para el repositorio: {repo_id}...")
    
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type=repo_type,
            private=False,
            exist_ok=True
        )
        print(f"[OK] Repositorio {repo_id} verificado/creado exitosamente.")
    except Exception as e:
        print(f"Error al crear el repositorio: {e}")
        return

    if os.path.exists("README.md"):
        print("Subiendo README.md (Dataset Card)...")
        api.upload_file(
            path_or_fileobj="README.md",
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="docs: update dataset card for HEKT-NOVA protocol"
        )
    
    data_file = "data/arca_symbolic_benchmark.jsonl"
    if os.path.exists(data_file):
        print("Subiendo archivo de datos arca_symbolic_benchmark.jsonl...")
        api.upload_file(
            path_or_fileobj=data_file,
            path_in_repo="data/arca_symbolic_benchmark.jsonl",
            repo_id=repo_id,
            repo_type=repo_type,
            commit_message="data: add validated JSONL benchmark test cases"
        )
        
    print("\n========================================")
    print(f" ¡Publicación completada con éxito!")
    print(f" URL: https://huggingface.co/datasets/{repo_id}")
    print("========================================")

if __name__ == "__main__":
    publish_to_huggingface()
