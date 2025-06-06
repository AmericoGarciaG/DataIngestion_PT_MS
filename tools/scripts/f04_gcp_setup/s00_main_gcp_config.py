# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s00_main_gcp_config.py
import sys
from pathlib import Path
import os

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts.f04_gcp_setup import s01_configure_sa_permissions as sa_perms
from tools.scripts.f04_gcp_setup import s02_manage_secrets as manage_secrets
from tools.scripts.f04_gcp_setup import s03_configure_workload_identity as configure_wif
# MODIFICADO: Incluir seed_firestore con importación absoluta
from tools.scripts.f05_data import seed_firestore

SCRIPT_PREFIX_S00_GCP_SETUP = "SCRIPT s00_gcp_setup: "

def main() -> bool:
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}--- INICIANDO CONFIGURACIÓN GCP POST-TERRAFORM (CON SEED DE DATOS) ---")
    
    if os.getenv("CI") is None: # No pedir input si está en un entorno CI
        input(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Este script configurará permisos de SA, secretos, WIF y poblará datos en Firestore.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Asegúrate de que Terraform apply se haya completado y 'service/.env' esté actualizado.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Presiona Enter para continuar o Ctrl+C para cancelar...")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 1: Configurando permisos de la Service Account...")
    if not sa_perms.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la configuración de permisos de la Service Account.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Permisos de Service Account configurados/verificados exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 2: Gestionando versiones de secretos en Secret Manager...")
    if not manage_secrets.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la gestión de secretos.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Gestión de secretos completada exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 3: Configurando binding de Workload Identity Federation...")
    if not configure_wif.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la configuración del binding de Workload Identity Federation.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Binding de Workload Identity Federation configurado exitosamente.")
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}IMPORTANTE: Asegúrate de configurar los SECRETOS impresos por el script anterior en tu repositorio de GitHub (Settings > Secrets and variables > Actions).")

    # MODIFICADO: Ejecutar seed_firestore.py como parte del flujo
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 4: Poblando Firestore con datos iniciales...")
    if not seed_firestore.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la población de datos en Firestore.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Población de datos en Firestore completada exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}--- CONFIGURACIÓN GCP POST-TERRAFORM (CON SEED DE DATOS) COMPLETADA EXITOSAMENTE ---")
    return True

if __name__ == "__main__":
    # Asegurarnos de que el directorio raíz del proyecto (donde está 'tools') esté en sys.path
    # si este script se ejecuta directamente de una forma que no lo añade
    # (ej. `python tools/scripts/f04_gcp_setup/s00_main_gcp_config.py`)
    # Esto es crucial para que `from tools.scripts import ...` funcione globalmente.
    current_script_path = Path(__file__).resolve()
    # PROJECT_ROOT/tools/scripts/f04_gcp_setup/s00_main_gcp_config.py
    # Queremos PROJECT_ROOT (DataIngestion_PT_MS) en sys.path
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent # Sube 4 niveles
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    
    if not main():
        sys.exit(1)