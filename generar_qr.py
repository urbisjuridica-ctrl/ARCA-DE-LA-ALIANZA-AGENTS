import qrcode
import json

datos_conexion = {
    "mcp_version": "1.0",
    "endpoint_target": "http://localhost:8000/consultar_oraculo",
    "method": "POST",
    "headers": {"Content-Type": "application/json"},
    "target_agent": "Agente Evangelista"
}

qr_data = json.dumps(datos_conexion, ensure_ascii=False, indent=2)
qr = qrcode.QRCode(version=1, box_size=10, border=5)
qr.add_data(qr_data)
qr.make(fit=True)

img = qr.make_image(fill_color="black", back_color="white")
img.save("qr_conexion_arca.png")
print("✅ [QR]: Matriz física regenerada correctamente apuntando a localhost.")
