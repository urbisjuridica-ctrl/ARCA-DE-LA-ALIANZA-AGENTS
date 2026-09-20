#!/bin/bash

if [ -z "$1" ]; then
    echo "🔴 Error: Debes incluir un mensaje para el commit entre comillas."
    echo "Ejemplo: ./actualizar_arca.sh \"feat: actualizacion\""
    exit 1
fi

echo "📦 1. Añadiendo cambios locales..."
git add .

echo "💾 2. Creando el registro (Commit)..."
git commit -m "$1" 2>/dev/null || echo "ℹ️ Nada nuevo que guardar localmente."

echo "🚀 3. Empujando los objetos criptográficos a GitHub..."
git push origin main

echo "🟢 Ecosistema local sincronizado y blindado en GitHub con éxito."
