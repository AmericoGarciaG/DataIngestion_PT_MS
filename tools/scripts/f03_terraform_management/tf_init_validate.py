# DataIngestion_PT_MS/tools/scripts/f03_terraform_management/tf_init_validate.py
import pathlib
import sys

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_TF_INIT = "SCRIPT tf_init_validate: " # Más específico

def main():
    print(f"{SCRIPT_PREFIX_TF_INIT}--- Terraform Init and Validate Script ---")
    
    project_root = ug.get_project_root()
    terraform_dir = project_root / "terraform"

    print(f"{SCRIPT_PREFIX_TF_INIT}Directorio de Terraform objetivo: {terraform_dir}")

    # Verificar existencia de archivos Terraform importantes
    required_tf_files = ["main.tf", "variables.tf", "versions.tf"] # outputs.tf es opcional
    missing_files = []
    for tf_file in required_tf_files:
        if not (terraform_dir / tf_file).exists():
            missing_files.append(tf_file)
    
    if missing_files:
        print(f"\n{SCRIPT_PREFIX_TF_INIT}ERROR: Faltan los siguientes archivos Terraform esenciales en '{terraform_dir}':")
        for f in missing_files:
            print(f"  - {f}")
        print(f"{SCRIPT_PREFIX_TF_INIT}Asegúrate de que la estructura del proyecto sea la correcta y los archivos .tf existan.")
        sys.exit(1)
    print(f"{SCRIPT_PREFIX_TF_INIT}[OK] Archivos Terraform requeridos encontrados.")

    # Inicializar Terraform
    print(f"\n{SCRIPT_PREFIX_TF_INIT}1. Ejecutando 'terraform init'...")
    if not ug.run_command_in_dir(["terraform", "init"], terraform_dir):
        # run_command_in_dir ya maneja la salida y el sys.exit si exit_on_error=True (default)
        return # O sys.exit(1) si quieres ser explícito aquí también

    # Validar configuración de Terraform
    print(f"\n{SCRIPT_PREFIX_TF_INIT}2. Ejecutando 'terraform validate'...")
    if not ug.run_command_in_dir(["terraform", "validate"], terraform_dir):
        return

    print(f"\n{SCRIPT_PREFIX_TF_INIT}===================================================")
    print(f"{SCRIPT_PREFIX_TF_INIT}Terraform inicializado y validado exitosamente en:\n  {terraform_dir}")
    print(f"{SCRIPT_PREFIX_TF_INIT}Ahora puedes ejecutar los scripts para 'plan' y 'apply'.")
    print(f"{SCRIPT_PREFIX_TF_INIT}===================================================")

if __name__ == "__main__":
    current_script_path = pathlib.Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    main()