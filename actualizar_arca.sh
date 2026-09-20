#!/bin/bash

# Verificar si el usuario ha introducido un mensaje para el commit
if [ -z "$1" ]; then
    echo "🔴 Error: Debes incluir un mensaje para el commit entre comillas."
    echo "Ejemplo: ./actualizar_arca.sh \"feat: actualizacion del firmware\""
    exit 1
fi

echo "📦 1. Añadiendo todos los cambios locales al flujo..."
git add .

echo "💾 2. Creando el registro de guardado (Commit)..."
git commit -m "$1"

echo "🚀 3. Empujando los objetos criptográficos directamente mediante URL absoluta..."
git push https://github.com main

echo "🟢 Ecosistema local sincronizado y blindado en GitHub con éxito."
