#!/usr/bin/env python3
"""
Script para desplegar el microservicio en Cloud Run.
"""

import os
import subprocess
from pathlib import Path

# Obtener el directorio raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVICE_DIR = PROJECT_ROOT / "service"

def run_command(cmd, cwd=None):
    """Ejecuta un comando y retorna su salida"""
    print(f"Ejecutando: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise Exception(f"Command failed with exit code {result.returncode}")
    return result.stdout.strip()

def deploy_to_cloud_run():
    """Despliega el servicio en Cloud Run"""
    # Verificar que estamos en el directorio correcto
    if not (SERVICE_DIR / "Dockerfile").exists():
        raise FileNotFoundError(f"No se encontró Dockerfile en {SERVICE_DIR}")

    # Construir y desplegar usando gcloud
    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        raise ValueError("PROJECT_ID environment variable not set")

    region = os.environ.get("REGION", "us-central1")
    service_name = "data-ingestion-pt-ms"

    try:
        print("\n=== Desplegando en Cloud Run ===")
        
        # Construir la imagen
        image_name = f"gcr.io/{project_id}/{service_name}"
        run_command(["gcloud", "builds", "submit", "--tag", image_name], cwd=SERVICE_DIR)
        
        # Desplegar en Cloud Run
        deploy_cmd = [
            "gcloud", "run", "deploy", service_name,
            "--image", image_name,
            "--platform", "managed",
            "--region", region,
            "--allow-unauthenticated"  # Solo si el servicio debe ser público
        ]
        
        run_command(deploy_cmd)
        print("\n✅ Despliegue completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante el despliegue: {e}")
        raise

if __name__ == "__main__":
    deploy_to_cloud_run()