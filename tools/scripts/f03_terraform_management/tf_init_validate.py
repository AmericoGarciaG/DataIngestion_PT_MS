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

'''
tf_init_validate.py
Propósito: Prepara el directorio de trabajo de Terraform. Primero, inicializa el directorio (terraform init), lo que descarga los proveedores necesarios y configura el backend de estado. Luego, valida la sintaxis y la coherencia de los archivos de configuración de Terraform (terraform validate).

Funcionamiento Principal:

Identificación del Directorio: Determina la ruta al directorio terraform/ dentro del proyecto.
Verificación de Archivos Esenciales: Comprueba la existencia de archivos clave de Terraform como main.tf, variables.tf, y versions.tf en el directorio terraform/. Si falta alguno, el script termina con un error.
Ejecución de terraform init:
Ejecuta el comando terraform init en el directorio terraform/ utilizando utils_general.run_command_in_dir.
Este comando prepara el directorio para otras operaciones de Terraform.
Ejecución de terraform validate:
Ejecuta el comando terraform validate en el directorio terraform/ utilizando utils_general.run_command_in_dir.
Este comando verifica que la configuración sea sintácticamente correcta y lógicamente consistente.
Dependencias:

CLI de terraform.
Módulo interno: tools.scripts.utils_general.
Uso (si se ejecuta directamente): Configura sys.path y llama a main().

Entradas:

Archivos de configuración de Terraform (*.tf) ubicados en el directorio terraform/.
Salidas y Efectos Secundarios:

Si terraform init se ejecuta por primera vez o hay cambios en proveedores/backend:
Crea o actualiza el subdirectorio .terraform/ con los plugins de los proveedores y la configuración del backend.
Puede interactuar con el backend de estado remoto si está configurado.
Imprime la salida de los comandos terraform init y terraform validate en la consola.
Mejores Prácticas y Consideraciones:

Primer Paso con Terraform: Este script (o los comandos que ejecuta) debe ser el primer paso al trabajar con una nueva configuración de Terraform o después de realizar cambios en las versiones de los proveedores o en la configuración del backend.
Instalación de Terraform: Asegurarse de que la CLI de Terraform esté instalada y accesible en el PATH.
Errores de Validación: Si terraform validate reporta errores, estos deben corregirse en los archivos .tf antes de proceder con plan o apply.
Backend de Estado: Prestar atención a la configuración del backend de estado en los archivos de Terraform, ya que init lo configurará.
'''