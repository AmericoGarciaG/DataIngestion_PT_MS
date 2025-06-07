# PROJECT_ROOT/tools/scripts/f03_terraform_management/tf_apply.py
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

SCRIPT_PREFIX_TF_APPLY = "SCRIPT tf_apply: " # Más específico

def main():
    print(f"{SCRIPT_PREFIX_TF_APPLY}--- Terraform Apply Script ---")
    
    project_root = ug.get_project_root()
    terraform_dir = project_root / "terraform"
    plan_file_path = terraform_dir / "tfplan.out"
    env_path = project_root / "service" / ".env" # Se lee para logging y confirmación de variables

    if not env_path.is_file():
        print(f"{SCRIPT_PREFIX_TF_APPLY}ERROR: Archivo 'service/.env' no encontrado en '{project_root / 'service'}'.")
        sys.exit(1)
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX_TF_APPLY}[INFO] Cargado 'service/.env' para confirmación de variables: {env_path}")


    gcp_project_id_for_log = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "ID_NO_ENCONTRADO_EN_ENV")

    if not plan_file_path.exists():
        print(f"{SCRIPT_PREFIX_TF_APPLY}ERROR: Archivo de plan '{plan_file_path}' no encontrado.")
        print(f"                 Por favor, ejecuta primero el script 'tf_plan.py' para generar el plan.")
        sys.exit(1)
        
    print(f"\n{SCRIPT_PREFIX_TF_APPLY}Aplicando plan de Terraform desde '{plan_file_path}'")
    print(f"                 para el proyecto (según .env): {gcp_project_id_for_log}")

    # Leer los IDs que tf_plan.py debería haber determinado y guardado/usado
    # Esto es para logging y confirmación, no para pasarlos directamente a 'terraform apply tfplan.out'
    # ya que el plan ya contiene estos valores.
    planned_wif_pool_id = os.getenv("WORKLOAD_IDENTITY_POOL_ID_FINAL")
    planned_wif_provider_id = os.getenv("WIF_PROVIDER_ID")

    if planned_wif_pool_id:
        print(f"                 Workload Identity Pool ID (según .env): {planned_wif_pool_id}")
    else:
        print(f"  {SCRIPT_PREFIX_TF_APPLY}ADVERTENCIA: WORKLOAD_IDENTITY_POOL_ID_FINAL no encontrado en 'service/.env'. Se usará lo que esté en el plan.")
    
    if planned_wif_provider_id:
        print(f"                 WIF Provider ID (según .env): {planned_wif_provider_id}")
    else:
        print(f"  {SCRIPT_PREFIX_TF_APPLY}ADVERTENCIA: WIF_PROVIDER_ID no encontrado en 'service/.env'. Se usará lo que esté en el plan (o el default de Terraform).")


    # Confirmación manual antes de aplicar
    confirm_input = input(f"\n{SCRIPT_PREFIX_TF_APPLY}¿Estás SEGURO de que quieres aplicar el plan '{plan_file_path.name}' al proyecto '{gcp_project_id_for_log}'? (Escribe 'yes' para confirmar): ").strip().lower()
    if confirm_input != 'yes':
        print(f"{SCRIPT_PREFIX_TF_APPLY}Apply cancelado por el usuario.")
        sys.exit(0)

    # El comando apply simplemente usa el archivo de plan.
    # No es necesario pasar -var de nuevo aquí, ya que están "cocinados" en el plan.
    apply_command = ["terraform", "apply", plan_file_path.name]
    # Si se desea -auto-approve para CI/CD o para evitar la confirmación de Terraform:
    # apply_command = ["terraform", "apply", "-auto-approve", plan_file_path.name]


    print(f"\n{SCRIPT_PREFIX_TF_APPLY}Ejecutando 'terraform apply' en el directorio '{terraform_dir}'...")
    
    # Usar ug.run_command_in_dir
    apply_successful = ug.run_command_in_dir(apply_command, terraform_dir, pass_through_stdio=True, exit_on_error=False)
    
    if not apply_successful:
        print(f"\n{SCRIPT_PREFIX_TF_APPLY}ERROR: 'terraform apply' falló. Revisa la salida de Terraform.")
        sys.exit(1) 
    
    print(f"\n{SCRIPT_PREFIX_TF_APPLY}===================================================")
    print(f"{SCRIPT_PREFIX_TF_APPLY}Terraform apply completado exitosamente desde '{plan_file_path.name}'.")
    print(f"                 La infraestructura de GCP para el proyecto '{gcp_project_id_for_log}' ha sido creada/actualizada.")
    if planned_wif_pool_id: # Reconfirmar con lo que estaba en .env
        print(f"                 Workload Identity Pool ID (de .env): {planned_wif_pool_id}")
    if planned_wif_provider_id:
        print(f"                 WIF Provider ID (de .env): {planned_wif_provider_id}")
    print(f"{SCRIPT_PREFIX_TF_APPLY}===================================================")

    # Opcional: eliminar el archivo de plan después de un apply exitoso
    # try:
    #     plan_file_path.unlink()
    #     print(f"{SCRIPT_PREFIX_TF_APPLY}Archivo de plan '{plan_file_path.name}' eliminado.")
    # except OSError as e:
    #     print(f"{SCRIPT_PREFIX_TF_APPLY}Advertencia: No se pudo eliminar el archivo de plan '{plan_file_path.name}': {e}")

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    main()

'''
tf_apply.py
Propósito: Aplica un plan de Terraform previamente generado y guardado (normalmente tfplan.out). Este script es el paso final para materializar los cambios de infraestructura definidos en la configuración de Terraform y validados en el plan.

Funcionamiento Principal:

Carga de Entorno: Carga el archivo service/.env. Esto se hace principalmente para propósitos de logging y para que el usuario confirme el proyecto sobre el cual se aplicarán los cambios.
Verificación del Plan: Comprueba si el archivo de plan (terraform/tfplan.out) existe. Si no, indica que se debe ejecutar tf_plan.py primero.
Confirmación del Usuario: Muestra el ID del proyecto (obtenido de .env) y el nombre del archivo de plan, y solicita una confirmación explícita del usuario (escribiendo "yes") antes de proceder con la aplicación.
Ejecución de terraform apply:
Construye el comando terraform apply tfplan.out (o terraform apply -auto-approve tfplan.out si se descomenta esa opción).
Ejecuta el comando en el directorio terraform/ utilizando utils_general.run_command_in_dir.
Variables de Entorno Clave (leídas de service/.env para logging/confirmación):

GOOGLE_CLOUD_PROJECT_ID
WORKLOAD_IDENTITY_POOL_ID_FINAL
WIF_PROVIDER_ID (Nota: Terraform utiliza los valores que están "cocinados" dentro del archivo tfplan.out para la aplicación, no los lee directamente de .env en este punto).
Dependencias:

CLI de terraform.
Módulo interno: tools.scripts.utils_general.
Uso (si se ejecuta directamente): Configura sys.path y llama a main().

Entradas:

Archivo de plan de Terraform: terraform/tfplan.out (generado por tf_plan.py).
Archivo service/.env (para confirmación del proyecto y logging).
Salidas y Efectos Secundarios:

Modifica la infraestructura en Google Cloud Platform de acuerdo con el plan de Terraform.
Imprime la salida del comando terraform apply en la consola.
Opcionalmente (si se descomenta), puede eliminar el archivo de plan tfplan.out después de una aplicación exitosa.
Mejores Prácticas y Consideraciones:

Revisión del Plan Obligatoria: Siempre se debe ejecutar tf_plan.py y revisar cuidadosamente el plan generado antes de ejecutar tf_apply.py.
Instalación de Terraform: Asegurarse de que la CLI de Terraform esté instalada.
Permisos: El usuario o el entorno donde se ejecuta Terraform (si es en CI/CD) debe tener los permisos necesarios en GCP para crear, modificar o eliminar los recursos definidos en la configuración de Terraform.
Confirmación Manual: La solicitud de confirmación manual es una medida de seguridad importante para evitar cambios accidentales en la infraestructura. Para entornos de CI/CD, se podría usar la opción -auto-approve.
Gestión del Estado: Asegurarse de que el backend de estado de Terraform esté correctamente configurado y accesible.
'''