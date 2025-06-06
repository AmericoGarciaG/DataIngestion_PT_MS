# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s00_main_gcp_config.py
import sys
from pathlib import Path
import os

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts.f04_gcp_setup import s01_configure_sa_permissions as sa_perms
from tools.scripts.f04_gcp_setup import s02_manage_secrets as manage_secrets
from tools.scripts.f04_gcp_setup import s03_configure_workload_identity as configure_wif
from tools.scripts.f04_gcp_setup import s04_set_github_secrets as set_gh_secrets
# NUEVA IMPORTACIÓN
from tools.scripts.f04_gcp_setup import s05_set_github_variables as set_gh_vars
from tools.scripts.f05_data import seed_firestore

SCRIPT_PREFIX_S00_GCP_SETUP = "SCRIPT s00_gcp_setup: "

def main() -> bool:
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}--- INICIANDO CONFIGURACIÓN GCP POST-TERRAFORM (CON SEED Y GITHUB SECRETS/VARS) ---")
    
    if os.getenv("CI") is None:
        input(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Este script configurará permisos, secretos, WIF, secretos/variables de GitHub y poblará datos.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Asegúrate de que 'gh' CLI esté autenticada y 'service/.env' esté actualizado.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Presiona Enter para continuar o Ctrl+C para cancelar...")

    # PASO 1 y 2 (sin cambios)
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 1: Configurando permisos de la Service Account...")
    if not sa_perms.main():
        # ...
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Permisos de Service Account configurados/verificados.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 2: Gestionando versiones de secretos en Secret Manager...")
    if not manage_secrets.main():
        # ...
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Gestión de secretos completada.")

    # PASO 3 (sin cambios)
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 3: Configurando binding de Workload Identity Federation...")
    success_wif, wif_provider, sa_email, project_id = configure_wif.main()
    if not success_wif:
        # ...
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Binding de Workload Identity Federation configurado.")

    # PASO 4 (sin cambios)
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 4: Configurando secretos en el repositorio de GitHub...")
    if project_id is None or wif_provider is None or sa_email is None:
        # ...
        return False
    if not set_gh_secrets.main(project_id, wif_provider, sa_email):
        # ...
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Secretos de GitHub configurados exitosamente.")

    # ===== INICIO DE LA CORRECCIÓN =====
    # NUEVO PASO PARA LAS VARIABLES
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 5: Configurando variables en el repositorio de GitHub...")
    if not set_gh_vars.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la configuración de variables en GitHub.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Variables de GitHub configuradas exitosamente.")
    
    # Renumerar el último paso
    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 6: Poblando Firestore con datos iniciales...")
    # ===== FIN DE LA CORRECCIÓN =====
    if not seed_firestore.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la población de datos en Firestore.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}[OK] Población de datos en Firestore completada.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}--- CONFIGURACIÓN GCP POST-TERRAFORM (CON SEED Y GITHUB SECRETS/VARS) COMPLETADA EXITOSAMENTE ---")
    return True

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    
    if not main():
        sys.exit(1)