#!/bin/sh

# Si PORT no está definido, usar 8080 por defecto
PORT="${PORT:-8080}"

# Iniciar uvicorn con el puerto configurado
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
