# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s04_set_github_secrets.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Importaciones absolutas desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_GH_SECRETS = "SCRIPT s04_gh_secrets: "

def main(project_id: str, wif_provider_name: str, sa_email: str) -> bool:
    """
    Configura los secretos necesarios para el workflow de CI/CD en el repositorio de GitHub.
    Utiliza la CLI de GitHub ('gh') que debe estar instalada y autenticada.

    Args:
        project_id: El ID del proyecto de GCP.
        wif_provider_name: El nombre completo del Workload Identity Provider.
        sa_email: El email de la Service Account a ser impersonada.

    Returns:
        True si todos los secretos se configuraron exitosamente, False en caso contrario.
    """
    print(f"{SCRIPT_PREFIX_GH_SECRETS}--- Iniciando Configuración de Secretos en Repositorio GitHub ---")
    project_root = ug.get_project_root()
    
    # Esta parte se puede simplificar, ya que el orquestador principal la llama
    # Vamos a usar la importación que ya tenías
    # Importar s03_setup_github_repo.py para usar su función de chequeo de 'gh'
    # Esto es un poco inusual pero funciona para reutilizar la lógica sin moverla a utils
    s03_setup_script_path = project_root / "tools" / "scripts" / "f00_files_setup"
    if str(s03_setup_script_path) not in sys.path:
        sys.path.insert(0, str(s03_setup_script_path))

    try:
        from tools.scripts.f00_files_setup import s03_setup_github_repo as sgr
        if not sgr.check_gh_cli_installed():
            print(f"{SCRIPT_PREFIX_GH_SECRETS}ERROR: La CLI de GitHub ('gh') no está instalada o autenticada.")
            print(f"       Por favor, ejecuta 'gh auth login' y reintenta.")
            return False
    except ImportError as e:
        print(f"{SCRIPT_PREFIX_GH_SECRETS}ERROR: No se pudo importar 's03_setup_github_repo' para verificar la CLI 'gh': {e}")
        return False
    finally:
        # Limpiar el path para evitar conflictos
        if str(s03_setup_script_path) in sys.path:
            sys.path.remove(str(s03_setup_script_path))


    env_path = project_root / "service" / ".env"
    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_GH_SECRETS}ERROR: Archivo 'service/.env' no encontrado.")
        return False
    load_dotenv(env_path)

    github_owner = os.getenv("GITHUB_REPO_OWNER")
    github_repo_name = os.getenv("GITHUB_REPO_NAME")

    if not github_owner or not github_repo_name:
        print(f"{SCRIPT_PREFIX_GH_SECRETS}ERROR: GITHUB_REPO_OWNER y/o GITHUB_REPO_NAME no están definidos en 'service/.env'.")
        return False

    full_repo_name = f"{github_owner}/{github_repo_name}"
    print(f"{SCRIPT_PREFIX_GH_SECRETS}Repositorio GitHub objetivo: {full_repo_name}")

    secrets_to_set = {
        "GCP_PROJECT_ID": project_id,
        "GCP_WORKLOAD_IDENTITY_PROVIDER": wif_provider_name,
        "GCP_SERVICE_ACCOUNT_EMAIL": sa_email
    }

    all_successful = True
    
    # ===== INICIO DE LA CORRECCIÓN =====
    # Busca el ejecutable UNA VEZ fuera del bucle.
    # CORREGIDO: Buscar 'gh.exe' en Windows, no 'gh.cmd'.
    gh_exe = ug.shutil.which("gh.exe") if os.name == 'nt' else ug.shutil.which("gh")
    if not gh_exe:
        # Esta comprobación es por si acaso, aunque check_gh_cli_installed ya debería haber fallado.
        print(f"  {SCRIPT_PREFIX_GH_SECRETS}ERROR CRÍTICO: No se encontró el ejecutable 'gh' después de la verificación inicial.")
        return False
    # ===== FIN DE LA CORRECCIÓN =====

    for secret_name, secret_value in secrets_to_set.items():
        if not secret_value:
            print(f"  {SCRIPT_PREFIX_GH_SECRETS}[WARN] El valor para el secreto '{secret_name}' está vacío. Omitiendo.")
            all_successful = False
            continue
            
        print(f"  {SCRIPT_PREFIX_GH_SECRETS}Configurando secreto: '{secret_name}' en '{full_repo_name}'...")
        
        command = [gh_exe, "secret", "set", secret_name, "--repo", full_repo_name]
        
        try:
            process = ug.subprocess.run(
                command, 
                input=secret_value, 
                text=True, 
                capture_output=True, 
                check=True,
                encoding="utf-8",
                errors="replace" # Añadido para robustez
            )
            if process.stderr:
                 print(f"    {SCRIPT_PREFIX_GH_SECRETS}[INFO] Salida de 'gh': {process.stderr.strip()}")
            print(f"    {SCRIPT_PREFIX_GH_SECRETS}[OK] Secreto '{secret_name}' configurado/actualizado.")

        except ug.subprocess.CalledProcessError as e:
            print(f"    {SCRIPT_PREFIX_GH_SECRETS}ERROR: Falló la configuración del secreto '{secret_name}'.")
            print(f"      Stderr: {e.stderr.strip()}")
            all_successful = False
        except Exception as e:
            print(f"    {SCRIPT_PREFIX_GH_SECRETS}ERROR inesperado configurando '{secret_name}': {e}")
            all_successful = False

    if not all_successful:
        print(f"\n{SCRIPT_PREFIX_GH_SECRETS}--- Configuración de Secretos en GitHub Finalizada CON ERRORES ---")
    else:
        print(f"\n{SCRIPT_PREFIX_GH_SECRETS}--- Configuración de Secretos en GitHub Finalizada Exitosamente ---")
        
    return all_successful

if __name__ == "__main__":
    print("Este script está diseñado para ser llamado desde el orquestador 's00_main_gcp_config.py'")


'''
04_set_github_secrets.py
Propósito: Configura secretos en un repositorio de GitHub. Estos secretos son típicamente credenciales o información sensible necesaria para los workflows de CI/CD, como las claves para autenticarse con Google Cloud mediante Workload Identity Federation. Utiliza la CLI de GitHub (gh).

Funcionamiento Principal:

Recepción de Argumentos: Acepta project_id (ID del proyecto GCP), wif_provider_name (nombre completo del proveedor de Workload Identity) y sa_email (email de la Service Account a impersonar) como argumentos. Estos suelen ser pasados por un script orquestador.
Verificación de gh CLI: Comprueba si la CLI de gh está instalada y autenticada. Reutiliza la lógica de tools.scripts.f00_files_setup.s03_setup_github_repo para esta verificación.
Carga de Entorno: Carga service/.env para obtener GITHUB_REPO_OWNER y GITHUB_REPO_NAME.
Definición de Secretos: Un diccionario secrets_to_set mapea los nombres de los secretos de GitHub (ej. GCP_PROJECT_ID) a los valores recibidos como argumentos.
Configuración de Secretos:
Itera sobre secrets_to_set.
Si un valor de secreto está vacío, lo omite y registra una advertencia.
Construye y ejecuta el comando gh secret set <NOMBRE_SECRETO> --repo <OWNER/REPO>. El valor del secreto se pasa a través de la entrada estándar (stdin) del proceso gh.
Utiliza utils_general.subprocess.run para la ejecución.
Manejo de Errores: Registra si la configuración de algún secreto falla.
Argumentos de la Función main:

project_id: str: ID del proyecto GCP.
wif_provider_name: str: Nombre completo del proveedor de Workload Identity Federation.
sa_email: str: Email de la Service Account de GCP que será impersonada.
Variables de Entorno Clave (leídas de service/.env):

GITHUB_REPO_OWNER: Propietario del repositorio de GitHub.
GITHUB_REPO_NAME: Nombre del repositorio de GitHub.
Dependencias:

CLI de gh (GitHub).
Python dotenv.
Módulos internos: tools.scripts.utils_general y (para la verificación de gh) tools.scripts.f00_files_setup.s03_setup_github_repo.
Uso (si se ejecuta directamente): El bloque if __name__ == "__main__": imprime un mensaje indicando que el script está diseñado para ser llamado desde un orquestador, ya que requiere argumentos que normalmente no se pasarían por línea de comandos directa.

Entradas:

Argumentos project_id, wif_provider_name, sa_email pasados a la función main().
Archivo service/.env (para los detalles del repositorio).
Autenticación con la CLI de gh.
Salidas y Efectos Secundarios:

Crea o actualiza secretos en el repositorio de GitHub especificado.
Imprime mensajes de estado y logs.
Mejores Prácticas y Consideraciones:

Autenticación de gh: Es crucial que la CLI de gh esté instalada y autenticada (gh auth login) con permisos para establecer secretos en el repositorio objetivo.
Orquestación: Este script está diseñado para ser invocado por un script orquestador (como s00_main_gcp_config.py) que pueda proporcionar los valores de los secretos dinámicamente (ej. después de configurar Workload Identity Federation).
Seguridad: Los valores pasados a este script son sensibles. Asegurarse de que el flujo de datos sea seguro.
Uso Típico de Secretos: Los secretos configurados (GCP_PROJECT_ID, GCP_WORKLOAD_IDENTITY_PROVIDER, GCP_SERVICE_ACCOUNT_EMAIL) son los estándar utilizados por la acción google-github-actions/auth para autenticar workflows de GitHub en GCP.
Idempotencia: El comando gh secret set es idempotente; si el secreto ya existe, lo actualiza.
'''