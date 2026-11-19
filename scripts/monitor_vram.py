import torch
import os

def check_vram():
    print("==================================================")
    print("   MONITOR DE RECURSOS VRAM - HEKT-NOVA v2.1")
    print("==================================================")
    
    if not torch.cuda.is_available():
        print("[!] No se detectó ninguna GPU CUDA activa. El sistema está operando en CPU.")
        return

    device_id = torch.cuda.current_device()
    device_name = torch.cuda.get_device_name(device_id)
    total_vram = torch.cuda.get_device_properties(device_id).total_memory / (1024**3)
    allocated_vram = torch.cuda.memory_allocated(device_id) / (1024**2)
    reserved_vram = torch.cuda.memory_reserved(device_id) / (1024**2)

    print(f"[*] Dispositivo GPU : {device_name}")
    print(f"[*] VRAM Total      : {total_vram:.2f} GB")
    print(f"[*] VRAM Asignada   : {allocated_vram:.2f} MB")
    print(f"[*] VRAM Reservada  : {reserved_vram:.2f} MB")
    print("==================================================")

if __name__ == "__main__":
    check_vram()
