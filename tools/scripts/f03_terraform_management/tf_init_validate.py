# DataIngestion_PT_MS/scripts/f03_terraform_management/tf_init_validate.py
import pathlib
import sys
from ..utils_general import run_command_in_dir, get_project_root

def main():
    print("--- Terraform Init and Validate Script ---")
    
    project_root = get_project_root()
    terraform_dir = project_root / "terraform"

    print(f"Directorio de Terraform objetivo: {terraform_dir}")

    main_tf_path = terraform_dir / "main.tf"
    if not main_tf_path.exists():
        print(f"\nERROR: No se pudo encontrar 'main.tf' en: {main_tf_path}")
        print("Asegurate de que la estructura del proyecto sea la correcta y los archivos .tf existan.")
        sys.exit(1)
    print(f"'main.tf' encontrado en: {main_tf_path}")

    # Inicializar Terraform
    print("\n1. Ejecutando 'terraform init'...")
    if not run_command_in_dir(["terraform", "init"], terraform_dir):
        sys.exit(1) # La función run_command ya maneja la salida del script si exit_on_error=True

    if not run_command_in_dir(["terraform", "validate"], terraform_dir):
        sys.exit(1)

    print("\n===================================================")
    print(f"Terraform inicializado y validado exitosamente en:\n{terraform_dir}")
    print("Ahora puedes ejecutar los scripts para 'plan' y 'apply'.")
    print("===================================================")

if __name__ == "__main__":
    main()
    # input("\nPresiona Enter para continuar...") # Comentado para posible uso en CI/CD