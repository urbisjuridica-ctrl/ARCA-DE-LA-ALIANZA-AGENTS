import subprocess
u = 'https://huggingface.co'
subprocess.run(['git', 'remote', 'remove', 'hf'], capture_output=True)
subprocess.run(['git', 'remote', 'add', 'hf', u])
res = subprocess.run(['git', 'remote', '-v'], capture_output=True, text=True)
print('🏺 [ANTENA RECALIBRADA PARA HF]:\n', res.stdout)
