import json, sys
from hekt_external_verifier import verify_message

def main():
    if len(sys.argv) < 2:
        print("Uso: hekt-verify '<cabecera HEKT-NOVA>' [ruta_artefacto]")
        sys.exit(1)
    raw = open(sys.argv[2], "rb").read() if len(sys.argv) > 2 else None
    res = verify_message(sys.argv[1], canonical_bytes=raw)
    print(json.dumps(res.__dict__, ensure_ascii=False, indent=2))
    sys.exit(0 if res.status == "VALID" else 2)

if __name__ == "__main__":
    main()
