# PROJECT_ROOT/scripts/f03_terraform_management/tf_plan.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv, set_key, find_dotenv # Asegúrate de tener python-dotenv instalado
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from utils_general import run_command_in_dir, get_project_root, find_available_resource_suffix, _check_wif_pool_exists_in_gcp # Importar utilidades

def main():
    print("--- Terraform Plan Script ---")
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"
    env_path = project_root / "service" / ".env" # Ruta al archivo .env

    if not env_path.is_file():
        print(f"SCRIPT tf_plan: ERROR: Archivo .env no encontrado en '{project_root}/service/'.")
        print(f"                Por favor, crea el archivo .env con las variables de configuración necesarias.")
        sys.exit(1)
    
    load_dotenv(env_path) # Cargar variables existentes de .env
    
    # Leer variables necesarias de .env para la lógica de este script
    gcp_project_id_from_env = os.getenv("GOOGLE_CLOUD_PROJECT_ID", None) 
    wif_pool_base_name = os.getenv("WIF_POOL_BASE_NAME", None) 
    wif_start_suffix_str = os.getenv("WIF_POOL_START_SUFFIX", None)
    
    # Validar que las variables para la lógica del WIF Pool ID existan
    if gcp_project_id_from_env is None:
        print("SCRIPT tf_plan: ERROR: GOOGLE_CLOUD_PROJECT_ID no está definida en .env.")
        sys.exit(1)
    if wif_pool_base_name is None:
        print("SCRIPT tf_plan: ERROR: WIF_POOL_BASE_NAME no está definida en .env.")
        sys.exit(1)
    if wif_start_suffix_str is None:
        print("SCRIPT tf_plan: ERROR: WIF_POOL_START_SUFFIX no está definida en .env.")
        sys.exit(1)

    try:
        wif_start_suffix_int = int(wif_start_suffix_str)
    except ValueError:
        print(f"SCRIPT tf_plan: ERROR: WIF_POOL_START_SUFFIX ('{wif_start_suffix_str}') en .env no es un número válido.")
        sys.exit(1)

    # Determinar el sufijo disponible para el Workload Identity Pool
    print(f"\nSCRIPT tf_plan: Buscando sufijo disponible para Workload Identity Pool...")
    print(f"                (Base: '{wif_pool_base_name}', Inicio Sufijo: {wif_start_suffix_int}, Proyecto: '{gcp_project_id_from_env}')")

    # Aquí aseguramos que todos los argumentos posicionales vayan primero
    effective_wif_suffix_str = find_available_resource_suffix(
        wif_pool_base_name,          # base_name (posicional)
        wif_start_suffix_int,        # start_suffix_int (posicional)
        20,                          # max_attempts (posicional)
        _check_wif_pool_exists_in_gcp,  # check_existence_func (posicional)
        3,                           # suffix_format_zeros (posicional)
        gcp_project_id_from_env      # check_func_args (posicional)
    )

    if effective_wif_suffix_str is None:
        print("SCRIPT tf_plan: ERROR: No se pudo determinar un sufijo único para el Workload Identity Pool.")
        sys.exit(1)
    
    final_workload_identity_pool_id = f"{wif_pool_base_name}-{effective_wif_suffix_str}"
    print(f"SCRIPT tf_plan: [INFO] Workload Identity Pool ID determinado para usar: {final_workload_identity_pool_id}")

    # Guardar/Actualizar WORKLOAD_IDENTITY_POOL_ID_FINAL en .env
    try:
        # find_dotenv busca hacia arriba, es más seguro pasar la ruta absoluta
        # set_key devuelve True si la clave se actualizó o añadió, False si el archivo no existe.
        if set_key(str(env_path), "WORKLOAD_IDENTITY_POOL_ID_FINAL", final_workload_identity_pool_id, quote_mode="never"):
            print(f"SCRIPT tf_plan: [INFO] WORKLOAD_IDENTITY_POOL_ID_FINAL='{final_workload_identity_pool_id}' guardado/actualizado en '{env_path}'.")
        else:
            print(f"SCRIPT tf_plan: ADVERTENCIA: No se pudo guardar WORKLOAD_IDENTITY_POOL_ID_FINAL en '{env_path}'.")
    except Exception as e:
        print(f"SCRIPT tf_plan: ADVERTENCIA: Excepción al guardar WORKLOAD_IDENTITY_POOL_ID_FINAL en .env: {e}")

    # Variables que se pasarán a Terraform con el flag -var
    terraform_variables_to_pass = {
        "gcp_project_id": gcp_project_id_from_env,
        "gcp_region": os.getenv("GCP_REGION", None),
        "app_sa_name": os.getenv("APP_SA_NAME", None),
        "workload_identity_pool_id_final": final_workload_identity_pool_id,
        "wif_provider_id": os.getenv("WIF_PROVIDER_ID", None),
        "github_repo_owner": os.getenv("GITHUB_REPO_OWNER", None),
        "github_repo_name": os.getenv("GITHUB_REPO_NAME", None),
        "firestore_location_id": os.getenv("FIRESTORE_LOCATION_ID", None),
        "artifact_registry_repository_name": os.getenv("ARTIFACT_REGISTRY_REPOSITORY_NAME", None),
        "pubsub_topic_name": os.getenv("PUBSUB_TOPIC_NAME", None),
        "cloud_run_service_name": os.getenv("CLOUD_RUN_SERVICE_NAME", None)
    }

    # Validar variables
    print("\nSCRIPT tf_plan: Verificando variables de entorno para Terraform...")
    missing_tf_vars = []
    for tf_var_name, env_value in terraform_variables_to_pass.items():
        if env_value is None and tf_var_name != "workload_identity_pool_id_final":
            missing_tf_vars.append(tf_var_name)

    if missing_tf_vars:
        print(f"SCRIPT tf_plan: ERROR: Las siguientes variables requeridas no se encontraron en .env o no tienen valor:")
        for var_name in missing_tf_vars:
            print(f"                 - {var_name}")
        sys.exit(1)
    print("SCRIPT tf_plan: [OK] Todas las variables necesarias para Terraform parecen estar disponibles.")

    print(f"\nSCRIPT tf_plan: Usando GCP Project ID para el plan: {terraform_variables_to_pass['gcp_project_id']}")

    terraform_var_args_list = []
    for tf_var_name, env_value in terraform_variables_to_pass.items():
        if env_value is not None:
            terraform_var_args_list.append(f"-var={tf_var_name}={env_value}")

    plan_command_list = ["terraform", "plan"] + terraform_var_args_list + ["-out=tfplan.out"]
    
    print(f"\nSCRIPT tf_plan: Ejecutando Terraform plan en directorio: {terraform_dir}")
    
    if not run_command_in_dir(plan_command_list, terraform_dir, pass_through_stdio=True, exit_on_error=False):
        print("\nSCRIPT tf_plan: ADVERTENCIA: 'terraform plan' finalizó con problemas o no generó cambios.")
        print("                  Revisa la salida de Terraform para más detalles.")
    else:
        print("\n===================================================")
        print("SCRIPT tf_plan: 'terraform plan' completado.")
        print("                El plan se ha guardado en 'terraform/tfplan.out'.")
        print(f"                Workload Identity Pool ID: {final_workload_identity_pool_id}")
        print(f"                WIF Provider ID: {terraform_variables_to_pass['wif_provider_id']}")
        print("                Revisa la salida de Terraform para ver los cambios propuestos.")
        print("                Para aplicar, ejecuta el script 'tf_apply.py'.")
        print("===================================================")

if __name__ == "__main__":
    main()