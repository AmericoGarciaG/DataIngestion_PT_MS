# PROJECT_ROOT/scripts/f03_terraform_management/tf_apply.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv # Para cargar variables para logging/confirmación
from ..utils_general import run_command_in_dir, get_project_root # Asumiendo que get_input está en utils_general si se usa

def main():
    print("--- Terraform Apply Script ---")
    
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"
    plan_file_path = terraform_dir / "tfplan.out"
    env_path = project_root / ".env"

    if not env_path.is_file():
        print(f"SCRIPT tf_apply: ERROR: Archivo .env no encontrado en '{project_root}'.")
        sys.exit(1)
    load_dotenv(env_path) # Cargar para obtener el project_id para log y los IDs a confirmar

    gcp_project_id_for_log = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "ID_NO_ENCONTRADO_EN_ENV")

    if not plan_file_path.exists():
        print(f"SCRIPT tf_apply: ERROR: Archivo de plan '{plan_file_path}' no encontrado.")
        print("                 Por favor, ejecuta primero el script 'tf_plan.py' para generar el plan.")
        sys.exit(1)
        
    print(f"SCRIPT tf_apply: Aplicando plan de Terraform desde '{plan_file_path}'")
    print(f"                 para el proyecto (según .env): {gcp_project_id_for_log}")

    # Leer los IDs que tf_plan.py debería haber determinado y guardado/usado
    # Esto es para logging y confirmación, no para pasarlos a 'terraform apply tfplan.out'
    planned_wif_pool_id = os.getenv("WORKLOAD_IDENTITY_POOL_ID_FINAL")
    planned_wif_provider_id = os.getenv("WIF_PROVIDER_ID")

    if planned_wif_pool_id:
        print(f"                 Workload Identity Pool ID en el plan: {planned_wif_pool_id}")
    else:
        print(f"SCRIPT tf_apply: ADVERTENCIA: WORKLOAD_IDENTITY_POOL_ID_FINAL no encontrado en .env. Se usará lo que esté en el plan.")
    
    if planned_wif_provider_id:
        print(f"                 WIF Provider ID en el plan: {planned_wif_provider_id}")
    else:
        print(f"SCRIPT tf_apply: ADVERTENCIA: WIF_PROVIDER_ID no encontrado en .env. Se usará lo que esté en el plan (o el default de Terraform).")


    # Confirmación manual antes de aplicar
    # Si se quiere importar get_input de utils_general: from ..utils_general import get_input
    # Por ahora, un input simple.
    confirm_input = input(f"\nSCRIPT tf_apply: ¿Estás SEGURO de que quieres aplicar el plan '{plan_file_path.name}'? (Escribe 'yes' para confirmar): ").strip().lower()
    if confirm_input != 'yes':
        print("SCRIPT tf_apply: Apply cancelado por el usuario.")
        sys.exit(0)

    apply_command = ["terraform", "apply", plan_file_path.name]
    # Si se desea -auto-approve para CI/CD o para evitar la confirmación de Terraform:
    # apply_command = ["terraform", "apply", "-auto-approve", plan_file_path.name]


    print("\nSCRIPT tf_apply: Ejecutando 'terraform apply'...")
    # print(f"SCRIPT tf_apply: Comando: {' '.join(apply_command)}") # Descomentar para depuración

    apply_successful = run_command_in_dir(apply_command, terraform_dir, pass_through_stdio=True, exit_on_error=False)
    
    if not apply_successful:
        print("\nSCRIPT tf_apply: ERROR: 'terraform apply' falló. Revisa la salida de Terraform.")
        sys.exit(1) 
    
    print("\n===================================================")
    print(f"SCRIPT tf_apply: Terraform apply completado exitosamente desde '{plan_file_path.name}'.")
    print("                 La infraestructura de GCP ha sido creada/actualizada.")
    if planned_wif_pool_id:
        print(f"                 Workload Identity Pool ID aplicado: {planned_wif_pool_id}")
    if planned_wif_provider_id:
        print(f"                 WIF Provider ID aplicado: {planned_wif_provider_id}")
    print("===================================================")

    # Opcional: eliminar el archivo de plan después de un apply exitoso
    # try:
    #     plan_file_path.unlink()
    #     print(f"SCRIPT tf_apply: Archivo de plan '{plan_file_path.name}' eliminado.")
    # except OSError as e:
    #     print(f"SCRIPT tf_apply: Advertencia: No se pudo eliminar el archivo de plan '{plan_file_path.name}': {e}")

if __name__ == "__main__":
    main()