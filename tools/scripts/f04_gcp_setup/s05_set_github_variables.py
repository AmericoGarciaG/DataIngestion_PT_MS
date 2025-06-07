# PROJECT_ROOT/tools/scripts/f04_gcp_setup/s05_set_github_variables.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Importaciones absolutas desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_GH_VARS = "SCRIPT s05_gh_vars: "

def main() -> bool:
    """
    Configura las variables de CI/CD (no secretas) en el repositorio de GitHub.
    Lee las variables desde 'service/.env' y las establece usando la CLI 'gh'.
    """
    print(f"{SCRIPT_PREFIX_GH_VARS}--- Iniciando Configuración de Variables en Repositorio GitHub ---")
    project_root = ug.get_project_root()
    env_path = project_root / "service" / ".env"

    if not env_path.exists():
        print(f"{SCRIPT_PREFIX_GH_VARS}ERROR: Archivo 'service/.env' no encontrado.")
        return False
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_GH_VARS}[INFO] Cargado 'service/.env' desde: {env_path}")

    github_owner = os.getenv("GITHUB_REPO_OWNER")
    github_repo_name = os.getenv("GITHUB_REPO_NAME")

    if not github_owner or not github_repo_name:
        print(f"{SCRIPT_PREFIX_GH_VARS}ERROR: GITHUB_REPO_OWNER y/o GITHUB_REPO_NAME no están definidos en 'service/.env'.")
        return False

    full_repo_name = f"{github_owner}/{github_repo_name}"
    print(f"{SCRIPT_PREFIX_GH_VARS}Repositorio GitHub objetivo: {full_repo_name}")

    # Mapeo de [Nombre de Variable en GitHub] -> [Nombre de Variable en .env]
    # Esto nos da flexibilidad si los nombres no coinciden exactamente.
    variables_map = {
        "GAR_LOCATION": "GCP_REGION",
        "SERVICE_NAME": "CLOUD_RUN_SERVICE_NAME",
        "ARTIFACT_REGISTRY_REPO_NAME": "ARTIFACT_REGISTRY_REPOSITORY_NAME",
        "ALPACA_PAPER": "ALPACA_PAPER",
        "ALPACA_ASSET_SYMBOL": "ALPACA_ASSET_SYMBOL",
        "FETCH_TIMEFRAME_STR": "FETCH_TIMEFRAME_STR",
        "FETCH_DAYS_HISTORY": "FETCH_DAYS_HISTORY",
        "SCHEDULE_TRIGGER": "SCHEDULE_TRIGGER",
        "SCHEDULE_HOUR": "SCHEDULE_HOUR",
        "SCHEDULE_MINUTE": "SCHEDULE_MINUTE",
        "PUBSUB_TOPIC_NAME": "PUBSUB_TOPIC_NAME",
        "FIRESTORE_PROVIDERS_COLLECTION": "FIRESTORE_PROVIDERS_COLLECTION",
        "FIRESTORE_ASSETS_COLLECTION": "FIRESTORE_ASSETS_COLLECTION",
    }
    
    all_successful = True
    gh_exe = ug.shutil.which("gh.exe") if os.name == 'nt' else ug.shutil.which("gh")
    if not gh_exe:
        print(f"  {SCRIPT_PREFIX_GH_VARS}ERROR CRÍTICO: No se encontró el ejecutable 'gh'.")
        return False

    for gh_var_name, env_var_name in variables_map.items():
        var_value = os.getenv(env_var_name)
        
        if var_value is None:
            print(f"  {SCRIPT_PREFIX_GH_VARS}[WARN] Variable de entorno '{env_var_name}' no encontrada en .env. Omitiendo '{gh_var_name}'.")
            continue
            
        print(f"  {SCRIPT_PREFIX_GH_VARS}Configurando variable: '{gh_var_name}' en '{full_repo_name}'...")
        
        # El comando `gh variable set` usa el flag --body para el valor.
        command = [gh_exe, "variable", "set", gh_var_name, "--body", var_value, "--repo", full_repo_name]
        
        try:
            process = ug.subprocess.run(
                command, 
                text=True, 
                capture_output=True, 
                check=True,
                encoding="utf-8",
                errors="replace"
            )
            if process.stderr:
                 print(f"    {SCRIPT_PREFIX_GH_VARS}[INFO] Salida de 'gh': {process.stderr.strip()}")
            print(f"    {SCRIPT_PREFIX_GH_VARS}[OK] Variable '{gh_var_name}' configurada/actualizada.")

        except ug.subprocess.CalledProcessError as e:
            print(f"    {SCRIPT_PREFIX_GH_VARS}ERROR: Falló la configuración de la variable '{gh_var_name}'.")
            print(f"      Stderr: {e.stderr.strip()}")
            all_successful = False
        except Exception as e:
            print(f"    {SCRIPT_PREFIX_GH_VARS}ERROR inesperado configurando '{gh_var_name}': {e}")
            all_successful = False

    if not all_successful:
        print(f"\n{SCRIPT_PREFIX_GH_VARS}--- Configuración de Variables en GitHub Finalizada CON ERRORES ---")
    else:
        print(f"\n{SCRIPT_PREFIX_GH_VARS}--- Configuración de Variables en GitHub Finalizada Exitosamente ---")
        
    return all_successful

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))

    if not main():
        sys.exit(1)


'''
s05_set_github_variables.py
Propósito: Configura variables de entorno (no secretas) en un repositorio de GitHub. Estas variables son típicamente utilizadas por los workflows de CI/CD (GitHub Actions). El script lee un mapeo de nombres de variables de GitHub a nombres de variables en el archivo service/.env y utiliza la CLI de GitHub (gh) para establecerlas.

Funcionamiento Principal:

Carga de Entorno: Carga el archivo service/.env.
Obtención de Detalles del Repositorio: Lee GITHUB_REPO_OWNER y GITHUB_REPO_NAME de .env para identificar el repositorio objetivo.
Iteración sobre el Mapeo de Variables:
Utiliza un diccionario variables_map que define la correspondencia: {"NOMBRE_EN_GITHUB": "NOMBRE_EN_DOTENV"}.
Para cada entrada en el mapa:
Obtiene el valor de la variable del entorno (cargado desde .env).
Si el valor no se encuentra en .env, omite la configuración de esa variable en GitHub y muestra una advertencia.
Construye y ejecuta el comando gh variable set <NOMBRE_EN_GITHUB> --body "<VALOR>" --repo <OWNER/REPO> utilizando utils_general.run_command_in_dir (aunque en la versión proporcionada, usa subprocess.run directamente).
Manejo de Errores: Registra si la configuración de alguna variable falla.
Variables de Entorno Clave (leídas de service/.env):

GITHUB_REPO_OWNER: Propietario del repositorio de GitHub.
GITHUB_REPO_NAME: Nombre del repositorio de GitHub.
Todas las variables listadas como valores en el diccionario variables_map (ej. GCP_REGION, CLOUD_RUN_SERVICE_NAME, etc.).
Constantes Importantes:

variables_map: Diccionario que define qué variables de .env se deben configurar en GitHub y con qué nombre.
Dependencias:

CLI de gh (GitHub).
Python dotenv.
Módulo interno: tools.scripts.utils_general.
Uso (si se ejecuta directamente): Configura sys.path y llama a main(). Sale con código 1 si la configuración de alguna variable falla.

Entradas:

Archivo service/.env conteniendo los valores de las variables a configurar.
Autenticación con la CLI de gh.
Salidas y Efectos Secundarios:

Crea o actualiza variables en el repositorio de GitHub especificado.
Imprime mensajes de estado y logs, incluyendo la salida de la CLI gh.
Mejores Prácticas y Consideraciones:

Autenticación de gh: Asegurarse de que la CLI de gh esté instalada y autenticada (gh auth login) con permisos para establecer variables en el repositorio objetivo.
Variables No Secretas: Utilizar este script únicamente para variables de configuración que no sean sensibles. Para información sensible, usar el script s04_set_github_secrets.py.
Flexibilidad del Mapeo: El variables_map permite que los nombres de las variables en .env difieran de los nombres utilizados en los workflows de GitHub, lo cual es una buena práctica para desacoplar.
Idempotencia: El comando gh variable set es idempotente; si la variable ya existe con el mismo valor, no causa error. Si existe con un valor diferente, la actualiza.
'''