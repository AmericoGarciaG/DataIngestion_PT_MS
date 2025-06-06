#!/usr/bin/env python3
"""
Script para desplegar el microservicio en Cloud Run.
Asume que este script se encuentra en PROJECT_ROOT/tools/scripts/f06_deployment/deploy_cloud_run.py
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import subprocess

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_DEPLOY_CR = "SCRIPT deploy_cloud_run: "

# Variables de entorno que se leerán del .env o del entorno de ejecución
ENV_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_GCP_REGION = "GCP_REGION"
ENV_CLOUD_RUN_SERVICE_NAME = "CLOUD_RUN_SERVICE_NAME"
ENV_ARTIFACT_REGISTRY_REPOSITORY_NAME = "ARTIFACT_REGISTRY_REPOSITORY_NAME" # Necesario para construir el nombre de la imagen
ENV_ALLOW_UNAUTHENTICATED = "CLOUD_RUN_ALLOW_UNAUTHENTICATED" # Opcional, default False

def deploy_to_cloud_run() -> bool: # Añadido tipo de retorno
    """Despliega el servicio en Cloud Run"""
    print(f"{SCRIPT_PREFIX_DEPLOY_CR}--- Iniciando Despliegue en Cloud Run ---")
    project_root = ug.get_project_root()
    service_dir = project_root / "service" # Directorio donde está el Dockerfile y el código de la app
    env_path_service = project_root / "service" / ".env"

    if not env_path_service.is_file():
        print(f"{SCRIPT_PREFIX_DEPLOY_CR}ADVERTENCIA: Archivo '.env' no encontrado en '{service_dir / '.env'}'. "
              "Se dependerá de variables de entorno externas para la configuración del despliegue.")
    else:
        load_dotenv(env_path_service)
        print(f"{SCRIPT_PREFIX_DEPLOY_CR}[INFO] Cargado 'service/.env' desde: {env_path_service}")

    if not (service_dir / "Dockerfile").exists():
        print(f"{SCRIPT_PREFIX_DEPLOY_CR}ERROR: No se encontró 'Dockerfile' en {service_dir}")
        return False

    gcp_project_id = os.getenv(ENV_PROJECT_ID)
    gcp_region = os.getenv(ENV_GCP_REGION)
    cloud_run_service_name = os.getenv(ENV_CLOUD_RUN_SERVICE_NAME)
    artifact_registry_repo_name = os.getenv(ENV_ARTIFACT_REGISTRY_REPOSITORY_NAME)
    allow_unauthenticated_str = os.getenv(ENV_ALLOW_UNAUTHENTICATED, "false").lower()

    required_deploy_vars = {
        ENV_PROJECT_ID: gcp_project_id,
        ENV_GCP_REGION: gcp_region,
        ENV_CLOUD_RUN_SERVICE_NAME: cloud_run_service_name,
        ENV_ARTIFACT_REGISTRY_REPOSITORY_NAME: artifact_registry_repo_name
    }
    missing_deploy_vars = [name for name, value in required_deploy_vars.items() if value is None]
    if missing_deploy_vars:
        print(f"{SCRIPT_PREFIX_DEPLOY_CR}ERROR: Faltan las siguientes variables de entorno necesarias para el despliegue (deben estar en 'service/.env' o en el entorno):")
        for var_name in missing_deploy_vars:
            print(f"  - {var_name}")
        return False

    print(f"{SCRIPT_PREFIX_DEPLOY_CR}Configuración de despliegue:")
    print(f"  Proyecto GCP: {gcp_project_id}")
    print(f"  Región GCP: {gcp_region}")
    print(f"  Nombre del servicio Cloud Run: {cloud_run_service_name}")
    print(f"  Repositorio Artifact Registry: {artifact_registry_repo_name}")

    try:
        print(f"\n{SCRIPT_PREFIX_DEPLOY_CR}PASO 1: Construyendo la imagen Docker con Google Cloud Build y subiendo a Artifact Registry...")
        # Formato de imagen para Artifact Registry: {LOCATION}-docker.pkg.dev/{PROJECT_ID}/{REPOSITORY_ID}/{IMAGE_NAME_WITH_TAG}
        image_name_artifact_registry = f"{gcp_region}-docker.pkg.dev/{gcp_project_id}/{artifact_registry_repo_name}/{cloud_run_service_name}:latest"
        
        # El comando gcloud builds submit construye y sube la imagen.
        # El --tag especifica el nombre completo de la imagen en el registro.
        build_cmd = ["gcloud", "builds", "submit", "--tag", image_name_artifact_registry]
        if not ug.run_command_in_dir(build_cmd, service_dir, pass_through_stdio=True): # Cwd es service_dir donde está el Dockerfile
            print(f"{SCRIPT_PREFIX_DEPLOY_CR}ERROR: Falló la construcción y subida de la imagen Docker.")
            return False
        print(f"{SCRIPT_PREFIX_DEPLOY_CR}[OK] Imagen Docker construida y subida a: {image_name_artifact_registry}")
        
        print(f"\n{SCRIPT_PREFIX_DEPLOY_CR}PASO 2: Desplegando la imagen en Cloud Run...")
        deploy_cmd = [
            "gcloud", "run", "deploy", cloud_run_service_name, # type: ignore
            "--image", image_name_artifact_registry,
            "--platform", "managed",
            "--region", gcp_region, # type: ignore
            # Se recomienda gestionar las variables de entorno y secretos a través de Terraform
            # o la consola de Cloud Run, en lugar de pasarlas aquí directamente,
            # a menos que sean configuraciones muy específicas del despliegue.
            # "--set-env-vars", "KEY1=VALUE1,KEY2=VALUE2",
            # "--update-secrets=MY_SECRET=projects/PROJECT_ID/secrets/SECRET_ID/versions/latest",
            # La Service Account asociada a Cloud Run se configura en Terraform (module.cloud_run.service_account_email)
            # y se le dan los permisos necesarios.
        ]
        
        if allow_unauthenticated_str == "true":
            deploy_cmd.append("--allow-unauthenticated")
            print(f"  {SCRIPT_PREFIX_DEPLOY_CR}[INFO] El servicio se desplegará permitiendo acceso no autenticado.")
        else:
            deploy_cmd.append("--no-allow-unauthenticated") # Ser explícito
            print(f"  {SCRIPT_PREFIX_DEPLOY_CR}[INFO] El servicio se desplegará requiriendo autenticación (IAM).")
        
        if not ug.run_command_in_dir(deploy_cmd, project_root, pass_through_stdio=True): # Cwd puede ser project_root aquí
            print(f"{SCRIPT_PREFIX_DEPLOY_CR}ERROR: Falló el despliegue en Cloud Run.")
            return False
        
        print(f"\n{SCRIPT_PREFIX_DEPLOY_CR}--- Despliegue en Cloud Run completado exitosamente ---")
        try:
            service_url_cmd = ["gcloud", "run", "services", "describe", cloud_run_service_name, # type: ignore
                               "--platform", "managed", "--region", gcp_region, "--format", "value(status.url)"] # type: ignore
            # Para obtener la URL, necesitamos capturar la salida, no solo True/False
            process_url = subprocess.run(subprocess.list2cmdline(service_url_cmd) if os.name == 'nt' else service_url_cmd,
                                         cwd=str(project_root), capture_output=True, text=True, check=False,
                                         shell=(os.name == 'nt'), encoding="utf-8", errors="replace")
            if process_url.returncode == 0 and process_url.stdout.strip():
                print(f"{SCRIPT_PREFIX_DEPLOY_CR}URL del servicio desplegado: {process_url.stdout.strip()}")
            else:
                print(f"{SCRIPT_PREFIX_DEPLOY_CR}ADVERTENCIA: No se pudo obtener la URL del servicio después del despliegue. (stdout: {process_url.stdout.strip()}, stderr: {process_url.stderr.strip()})")
        except Exception as e_url:
            print(f"{SCRIPT_PREFIX_DEPLOY_CR}ADVERTENCIA: Excepción al intentar obtener la URL del servicio: {e_url}")
        return True
        
    except Exception as e:
        print(f"\n{SCRIPT_PREFIX_DEPLOY_CR}ERROR inesperado durante el despliegue: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))

    if not deploy_to_cloud_run():
        sys.exit(1)