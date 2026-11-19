import subprocess
url = "https://huggingface.co"
print("🏺 [ESTABLECIENDO PUNTERO ABSOLUTO INTERNO]")
subprocess.run(["git", "remote", "remove", "hf"], capture_output=True)
subprocess.run(["git", "remote", "add", "hf", url])
res = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
print(res.stdout)