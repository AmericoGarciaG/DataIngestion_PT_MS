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

'''
s00_main_gcp_config.py
Propósito: Actúa como un script orquestador principal para ejecutar una secuencia de tareas de configuración en GCP y GitHub. Está diseñado para ser ejecutado después de que la infraestructura base haya sido aprovisionada (generalmente mediante terraform apply).

Funcionamiento Principal:

Confirmación del Usuario: Si no se ejecuta en un entorno de CI (variable de entorno CI no definida), solicita al usuario que presione Enter para continuar, advirtiendo sobre las acciones que realizará.
Ejecución Secuencial de Scripts: Llama a las funciones main() de varios scripts de configuración en un orden específico:
s01_configure_sa_permissions.main(): Configura permisos para la SA de la aplicación.
s02_manage_secrets.main(): Gestiona versiones de secretos en Secret Manager.
s03_configure_workload_identity.main(): Configura el binding de Workload Identity Federation para la SA. Captura los valores devueltos (ID del proveedor WIF, email de la SA, ID del proyecto).
s04_set_github_secrets.main(): Utiliza los valores del paso anterior para configurar secretos en el repositorio de GitHub.
s05_set_github_variables.main(): Configura variables (no secretas) en el repositorio de GitHub.
seed_firestore.main(): Puebla Firestore con datos iniciales.
Manejo de Errores: Si alguno de los scripts llamados devuelve False (indicando un error), el script orquestador termina e informa del fallo.
Dependencias:

Módulos internos importados:
tools.scripts.f04_gcp_setup.s01_configure_sa_permissions
tools.scripts.f04_gcp_setup.s02_manage_secrets
tools.scripts.f04_gcp_setup.s03_configure_workload_identity
tools.scripts.f04_gcp_setup.s04_set_github_secrets
tools.scripts.f04_gcp_setup.s05_set_github_variables
tools.scripts.f05_data.seed_firestore
Implícitamente, depende de las herramientas y configuraciones que estos sub-scripts requieren (ej. gcloud ADC, gh CLI autenticada, archivo service/.env).
Uso (si se ejecuta directamente): Configura sys.path y llama a main(). Sale con código 1 si alguna de las tareas de configuración falla.

Entradas:

Indirectamente, el archivo service/.env (utilizado por los sub-scripts).
Autenticación con la CLI de gh (para los scripts que configuran secretos/variables de GitHub).
Credenciales ADC de gcloud (para los scripts que interactúan con GCP).
Salidas y Efectos Secundarios:

Agrega los efectos secundarios de todos los scripts que invoca (modificaciones en IAM de GCP, Secret Manager, Workload Identity, secretos/variables de GitHub, datos en Firestore).
Imprime mensajes de estado y logs detallados de cada paso.
Mejores Prácticas y Consideraciones:

Orden de Ejecución: Ejecutar este script después de que terraform apply haya completado exitosamente el aprovisionamiento de la infraestructura base.
Autenticación Previa: Asegurarse de que la CLI de gh esté instalada y autenticada (ej. con gh auth login) antes de ejecutar este script si se van a configurar secretos/variables de GitHub.
Credenciales ADC: Asegurarse de que las Credenciales Predeterminadas de Aplicación (gcloud auth application-default login) estén configuradas y tengan los permisos necesarios para todas las operaciones de GCP que realizan los sub-scripts.
Revisión de Sub-Scripts: Comprender lo que hace cada sub-script es importante antes de ejecutar este orquestador.
'''