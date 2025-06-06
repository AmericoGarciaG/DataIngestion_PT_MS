# PROJECT_ROOT/tools/scripts/f00_files_setup/s02_create_venv.py
import os
import subprocess
import sys
import pathlib

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

# Constantes globales para el script
# SCRIPT_FILE_PATH = pathlib.Path(__file__).resolve() # No se usa en este script
PROJECT_ROOT = ug.get_project_root()
SCRIPT_PREFIX = "SCRIPT s02_venv: " # Más específico
VENV_NAME = ".venv"


def run_command_for_venv(command_list, error_message="Command failed", working_directory=None) -> bool:
    """
    Ejecuta un comando específicamente para este script de venv.
    Devuelve True en éxito, False en fallo.
    """
    print(f"  {SCRIPT_PREFIX}[INFO]: Executing: {' '.join(command_list)}")
    try:
        process = subprocess.run(command_list, check=True, capture_output=True, text=True, cwd=working_directory, encoding="utf-8", errors="replace")
        if process.stderr and process.stderr.strip():
             print(f"  {SCRIPT_PREFIX}[STDERR]: {process.stderr.strip()}") # Útil para warnings de pip o venv
        # No imprimir stdout aquí, ya que a veces es muy verboso (ej. pip install)
        # print(f"  {SCRIPT_PREFIX}[STDOUT]: {process.stdout.strip()}")
        print(f"  {SCRIPT_PREFIX}[OK]: Command successful: {' '.join(command_list)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  {SCRIPT_PREFIX}ERROR: {error_message}")
        print(f"  {SCRIPT_PREFIX}  Return code: {e.returncode}")
        if e.stdout and e.stdout.strip(): print(f"  {SCRIPT_PREFIX}  STDOUT: {e.stdout.strip()}")
        if e.stderr and e.stderr.strip(): print(f"  {SCRIPT_PREFIX}  STDERR: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"  {SCRIPT_PREFIX}ERROR: Command not found: {command_list[0]}. Is Python (o el comando) in your PATH?")
        return False
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR: Unexpected error executing command: {e}")
        return False

def main() -> bool:
    """Crea el entorno virtual si no existe."""
    venv_path = PROJECT_ROOT / VENV_NAME

    print(f"{SCRIPT_PREFIX}--- Python Virtual Environment Creation ---")
    print(f"{SCRIPT_PREFIX}Project root: {PROJECT_ROOT}")

    # Usar el ejecutable de Python que está corriendo este script para crear el venv
    # Esto asegura consistencia si hay múltiples Pythons instalados.
    python_executable_to_create_venv = sys.executable
    print(f"\n{SCRIPT_PREFIX}1. Using Python interpreter for venv creation: {python_executable_to_create_venv}")

    print(f"\n{SCRIPT_PREFIX}2. Checking/Creating virtual environment at: {venv_path.relative_to(PROJECT_ROOT.parent)}")
    if not venv_path.is_dir():
        print(f"  {SCRIPT_PREFIX}[INFO] Virtual environment directory not found. Creating...")
        if not run_command_for_venv([python_executable_to_create_venv, "-m", "venv", str(venv_path)], "Failed to create venv.", working_directory=str(PROJECT_ROOT)):
            return False
        print(f"  {SCRIPT_PREFIX}[OK] Virtual environment created at '{venv_path.relative_to(PROJECT_ROOT)}'.")
    else:
        print(f"  {SCRIPT_PREFIX}[SKIP] Virtual environment directory '{venv_path.relative_to(PROJECT_ROOT)}' already exists.")

    # Verificar estructura básica del venv
    if os.name == 'nt':
        venv_python_exe_path = venv_path / "Scripts" / "python.exe"
    else:
        venv_python_exe_path = venv_path / "bin" / "python"

    if not venv_python_exe_path.is_file():
        print(f"  {SCRIPT_PREFIX}ERROR: Virtual environment at '{venv_path.relative_to(PROJECT_ROOT)}' seems incomplete or corrupted.")
        print(f"                 (Expected python executable at: {venv_python_exe_path})")
        print(f"                 Consider deleting the '{VENV_NAME}' directory and re-running this script.")
        return False
    print(f"  {SCRIPT_PREFIX}[OK]: Virtual environment structure appears valid (found python executable).")

    print(f"\n{SCRIPT_PREFIX}--- Virtual Environment Creation Finished ---")
    print(f"{SCRIPT_PREFIX}Virtual environment '{VENV_NAME}' is ready (or already existed) at '{PROJECT_ROOT}'.")
    # Las instrucciones para activar el venv se darán en el script orquestador (s00_main_initial_setup.py)
    # print(f"\n{SCRIPT_PREFIX}GUÍA: Para activar el entorno virtual...") (Eliminado de aquí)
    print("-" * 60)
    print(f"{SCRIPT_PREFIX}[INFO]: NEXT STEP: The main setup script will guide you to activate this venv.")
    print(f"                 After activation, you'll install project dependencies using 'requirements.txt'.")
    print("-" * 60)

    return True

if __name__ == "__main__":
    current_script_path = pathlib.Path(__file__).resolve()
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    if not main():
        sys.exit(1)