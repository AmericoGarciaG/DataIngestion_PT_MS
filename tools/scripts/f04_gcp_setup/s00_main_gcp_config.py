# PROJECT_ROOT/scripts/f04_gcp_setup/s00_main_gcp_config.py
import sys
from pathlib import Path
import os

# Importar los módulos de este paquete (f04_gcp_setup)
from . import s01_configure_sa_permissions as sa_perms       # Nuevo nombre
from . import s02_manage_secrets as manage_secrets           # Nuevo nombre
from . import s03_configure_workload_identity as configure_wif # Nuevo nombre
# utils_gcp.py se importa dentro de los scripts s0X_ si es necesario.

# Importar seed_firestore desde el paquete hermano f05_data
# sys.path.append(str(Path(__file__).resolve().parent.parent)) # Añadir 'scripts/' a sys.path
# from f05_data import seed_firestore # Asumiendo que seed_firestore está en scripts/f05_data/

# Alternativa para importar seed_firestore si está en scripts/data/ y la estructura es scripts/f05_data/
# Esto asume que 'scripts' es un paquete reconocible desde donde se ejecuta.
# Cuando se ejecuta con `python -m scripts.f04_gcp_setup.s00_main_gcp_config` desde la raíz,
# el directorio raíz del proyecto se añade a sys.path.
try:
    from scripts.f05_data import seed_firestore
except ImportError:
    # Fallback si la estructura es ligeramente diferente o para pruebas locales del script
    # Esto es un poco más frágil.
    grandparent_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(grandparent_dir)) # Añadir scripts/
    from f05_data import seed_firestore

SCRIPT_PREFIX_S00_GCP_SETUP = "SCRIPT s00_gcp_setup: " # Cambiado para reflejar la carpeta

def main() -> bool: # Añadir tipo de retorno    
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}--- INICIANDO CONFIGURACIÓN GCP POST-TERRAFORM ---")
    
    if os.getenv("CI") is None:
        input(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Este script configurará permisos de SA, secretos, WIF y poblará datos.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Asegúrate de que Terraform apply se haya completado y .env esté actualizado.\n"
              f"{SCRIPT_PREFIX_S00_GCP_SETUP}Presiona Enter para continuar o Ctrl+C para cancelar...")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 1: Configurando permisos de la Service Account...")
    if not sa_perms.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la configuración de permisos de la Service Account.")
        return False # Devolver False en lugar de sys.exit
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Permisos de Service Account configurados/verificados exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 2: Gestionando versiones de secretos en Secret Manager...")
    if not manage_secrets.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la gestión de secretos.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Gestión de secretos completada exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 3: Configurando binding de Workload Identity Federation...")
    if not configure_wif.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la configuración del binding de Workload Identity Federation.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Binding de Workload Identity Federation configurado exitosamente.")
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}IMPORTANTE: Asegúrate de configurar los SECRETOS impresos por el script anterior en tu repositorio de GitHub.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}PASO 4: Poblando Firestore con datos iniciales...")
    if not seed_firestore.main():
        print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}ERROR FATAL: Falló la población de datos en Firestore.")
        return False
    print(f"{SCRIPT_PREFIX_S00_GCP_SETUP}Población de datos en Firestore completada exitosamente.")

    print(f"\n{SCRIPT_PREFIX_S00_GCP_SETUP}--- CONFIGURACIÓN GCP POST-TERRAFORM COMPLETADA EXITOSAMENTE ---")
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1) # Salir con error si main() devuelve False