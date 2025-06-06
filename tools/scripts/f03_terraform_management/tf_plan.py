# PROJECT_ROOT/tools/scripts/f03_terraform_management/tf_plan.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, set_key # find_dotenv no es necesario si damos ruta explícita

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_TF_PLAN = "SCRIPT tf_plan: " # Más específico

def main():
    print(f"{SCRIPT_PREFIX_TF_PLAN}--- Terraform Plan Script ---")
    project_root = ug.get_project_root()
    terraform_dir = project_root / "terraform"
    env_path = project_root / "service" / ".env" # Ruta al archivo .env

    if not env_path.is_file():
        print(f"{SCRIPT_PREFIX_TF_PLAN}ERROR: Archivo 'service/.env' no encontrado en '{project_root / 'service'}'.")
        print(f"                Por favor, asegúrate de que exista y contenga las variables de configuración necesarias.")
        sys.exit(1)
    
    # Cargar .env ANTES de leer cualquier variable
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_TF_PLAN}[INFO] Cargado 'service/.env' desde: {env_path}")
    
    # Leer variables necesarias de .env para la lógica de este script
    gcp_project_id_from_env = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
    wif_pool_base_name = os.getenv("WIF_POOL_BASE_NAME")
    wif_start_suffix_str = os.getenv("WIF_POOL_START_SUFFIX")
    
    # Validar que las variables para la lógica del WIF Pool ID existan
    required_vars_for_wif_logic = {
        "GOOGLE_CLOUD_PROJECT_ID": gcp_project_id_from_env,
        "WIF_POOL_BASE_NAME": wif_pool_base_name,
        "WIF_POOL_START_SUFFIX": wif_start_suffix_str
    }
    missing_wif_vars = [name for name, value in required_vars_for_wif_logic.items() if value is None]
    if missing_wif_vars:
        print(f"{SCRIPT_PREFIX_TF_PLAN}ERROR: Faltan las siguientes variables en 'service/.env' para la lógica de WIF Pool ID:")
        for var_name in missing_wif_vars:
            print(f"                 - {var_name}")
        sys.exit(1)

    try:
        wif_start_suffix_int = int(wif_start_suffix_str) # type: ignore
    except ValueError:
        print(f"{SCRIPT_PREFIX_TF_PLAN}ERROR: WIF_POOL_START_SUFFIX ('{wif_start_suffix_str}') en 'service/.env' no es un número válido.")
        sys.exit(1)

    print(f"\n{SCRIPT_PREFIX_TF_PLAN}Buscando sufijo disponible para Workload Identity Pool...")
    print(f"                (Base: '{wif_pool_base_name}', Inicio Sufijo: {wif_start_suffix_int}, Proyecto: '{gcp_project_id_from_env}')")

    effective_wif_suffix_str = ug.find_available_resource_suffix(
        wif_pool_base_name, # type: ignore
        wif_start_suffix_int,
        20, # max_attempts
        ug._check_wif_pool_exists_in_gcp,
        3,  # suffix_format_zeros
        gcp_project_id_from_env # *check_func_args
    )

    if effective_wif_suffix_str is None:
        print(f"{SCRIPT_PREFIX_TF_PLAN}ERROR: No se pudo determinar un sufijo único para el Workload Identity Pool después de varios intentos.")
        sys.exit(1)
    
    final_workload_identity_pool_id = f"{wif_pool_base_name}-{effective_wif_suffix_str}" # type: ignore
    print(f"{SCRIPT_PREFIX_TF_PLAN}[OK] Workload Identity Pool ID determinado para usar: {final_workload_identity_pool_id}")

    # Guardar/Actualizar WORKLOAD_IDENTITY_POOL_ID_FINAL en .env
    # Esto es crucial porque terraform/main.tf lo leerá como variable.
    try:
        if set_key(str(env_path), "WORKLOAD_IDENTITY_POOL_ID_FINAL", final_workload_identity_pool_id, quote_mode="never"):
            print(f"{SCRIPT_PREFIX_TF_PLAN}[OK] WORKLOAD_IDENTITY_POOL_ID_FINAL='{final_workload_identity_pool_id}' guardado/actualizado en '{env_path}'.")
        else:
            # set_key devuelve False si el archivo .env no existe, pero ya verificamos esto.
            # Podría fallar por permisos, etc.
            print(f"{SCRIPT_PREFIX_TF_PLAN}ADVERTENCIA: No se pudo guardar WORKLOAD_IDENTITY_POOL_ID_FINAL en '{env_path}'. set_key devolvió False.")
    except Exception as e:
        print(f"{SCRIPT_PREFIX_TF_PLAN}ADVERTENCIA: Excepción al guardar WORKLOAD_IDENTITY_POOL_ID_FINAL en 'service/.env': {e}")

    # Definir explícitamente qué variables de Terraform esperamos del .env
    # Los nombres de las claves deben coincidir con las variables en variables.tf
    # Los valores se obtienen de os.getenv (que ya leyó el .env cargado)
    terraform_vars_from_env = {
        "gcp_project_id": os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
        "gcp_region": os.getenv("GCP_REGION"),
        "app_sa_name": os.getenv("APP_SA_NAME"),
        # "workload_identity_pool_id_final" se define arriba y se pasa directamente
        "wif_provider_id": os.getenv("WIF_PROVIDER_ID"),
        "github_repo_owner": os.getenv("GITHUB_REPO_OWNER"),
        "github_repo_name": os.getenv("GITHUB_REPO_NAME"),
        "firestore_location_id": os.getenv("FIRESTORE_LOCATION_ID"),
        "artifact_registry_repository_name": os.getenv("ARTIFACT_REGISTRY_REPOSITORY_NAME"),
        "pubsub_topic_name": os.getenv("PUBSUB_TOPIC_NAME"),
        "cloud_run_service_name": os.getenv("CLOUD_RUN_SERVICE_NAME")
    }
    # Añadir la variable determinada dinámicamente
    terraform_vars_from_env["workload_identity_pool_id_final"] = final_workload_identity_pool_id


    print(f"\n{SCRIPT_PREFIX_TF_PLAN}Verificando variables de entorno para Terraform...")
    missing_tf_vars = []
    terraform_var_args_list = []

    for tf_var_name, env_value in terraform_vars_from_env.items():
        if env_value is None:
            missing_tf_vars.append(tf_var_name.upper()) # Usar el nombre de la var de entorno para el mensaje
        else:
            terraform_var_args_list.append(f"-var={tf_var_name}={env_value}") # Construir los -var para terraform

    if missing_tf_vars:
        print(f"{SCRIPT_PREFIX_TF_PLAN}ERROR: Las siguientes variables (esperadas por Terraform) no se encontraron en 'service/.env' o no tienen valor:")
        for var_name_env in missing_tf_vars:
            # Tratar de encontrar el nombre de la variable Terraform correspondiente si es diferente
            tf_var_key = next((k for k, v_name in {"gcp_project_id": "GOOGLE_CLOUD_PROJECT_ID",
                                                "gcp_region": "GCP_REGION",
                                                "app_sa_name": "APP_SA_NAME",
                                                "workload_identity_pool_id_final": "WORKLOAD_IDENTITY_POOL_ID_FINAL", # Aunque no debería estar aquí
                                                "wif_provider_id": "WIF_PROVIDER_ID",
                                                "github_repo_owner": "GITHUB_REPO_OWNER",
                                                "github_repo_name": "GITHUB_REPO_NAME",
                                                "firestore_location_id": "FIRESTORE_LOCATION_ID",
                                                "artifact_registry_repository_name": "ARTIFACT_REGISTRY_REPOSITORY_NAME",
                                                "pubsub_topic_name": "PUBSUB_TOPIC_NAME",
                                                "cloud_run_service_name": "CLOUD_RUN_SERVICE_NAME"
                                                }.items() if v_name == var_name_env), var_name_env.lower())
            print(f"                 - Variable de entorno '{var_name_env}' (para Terraform var '{tf_var_key}')")
        sys.exit(1)
    print(f"{SCRIPT_PREFIX_TF_PLAN}[OK] Todas las variables necesarias para Terraform parecen estar disponibles.")
    print(f"{SCRIPT_PREFIX_TF_PLAN}Usando GCP Project ID para el plan: {terraform_vars_from_env['gcp_project_id']}")

    plan_command_list = ["terraform", "plan"] + terraform_var_args_list + ["-out=tfplan.out"]
    
    print(f"\n{SCRIPT_PREFIX_TF_PLAN}Ejecutando Terraform plan en directorio: {terraform_dir}")
    # Usar ug.run_command_in_dir para ejecutar el plan
    if not ug.run_command_in_dir(plan_command_list, terraform_dir, pass_through_stdio=True, exit_on_error=False):
        print(f"\n{SCRIPT_PREFIX_TF_PLAN}ADVERTENCIA: 'terraform plan' finalizó con problemas o no generó cambios.")
        print(f"                  Revisa la salida de Terraform para más detalles. El archivo 'tfplan.out' podría no haberse creado o estar incompleto.")
        # No salir necesariamente, pero el apply podría fallar o no hacer nada.
    else:
        print(f"\n{SCRIPT_PREFIX_TF_PLAN}===================================================")
        print(f"{SCRIPT_PREFIX_TF_PLAN}'terraform plan' completado.")
        print(f"                El plan se ha guardado en '{terraform_dir / 'tfplan.out'}'.")
        print(f"                Workload Identity Pool ID a usar: {final_workload_identity_pool_id}")
        print(f"                WIF Provider ID a usar: {terraform_vars_from_env.get('wif_provider_id', 'NO_DEFINIDO')}")
        print(f"                Revisa la salida de Terraform para ver los cambios propuestos.")
        print(f"                Para aplicar, ejecuta el script 'tf_apply.py'.")
        print(f"{SCRIPT_PREFIX_TF_PLAN}===================================================")

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    main()