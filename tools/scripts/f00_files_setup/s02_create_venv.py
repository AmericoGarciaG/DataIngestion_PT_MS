# PROJECT_ROOT/tools/scripts/f00_files_setup/s02_create_venv.py
import os
import subprocess
import sys
import pathlib

# Constantes globales para el script
SCRIPT_FILE_PATH = pathlib.Path(__file__).resolve()
# Asumimos que este script está en Project_Root/tools/scripts/f00_files_setup/
PROJECT_ROOT = SCRIPT_FILE_PATH.parent.parent.parent.parent # Sube de f00_... -> scripts -> tools -> PROJECT_ROOT
SCRIPT_PREFIX = "SCRIPT s02: "
VENV_NAME = ".venv" # Nombre estándar para venv

def run_command_for_venv(command_list, error_message="Command failed", working_directory=None) -> bool:
    """
    Ejecuta un comando específicamente para este script de venv.
    Devuelve True en éxito, False en fallo.
    """
    print(f"  {SCRIPT_PREFIX}[INFO]: Executing: {' '.join(command_list)}")
    try:
        process = subprocess.run(command_list, check=True, capture_output=True, text=True, cwd=working_directory, encoding="utf-8", errors="replace")
        if process.stderr and process.stderr.strip():
             print(f"  {SCRIPT_PREFIX}[STDERR]: {process.stderr.strip()}")
        print(f"  {SCRIPT_PREFIX}[OK]: Command successful: {' '.join(command_list)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  {SCRIPT_PREFIX}[ERROR]: {error_message}")
        print(f"  {SCRIPT_PREFIX}[ERROR]: Return code: {e.returncode}")
        if e.stdout and e.stdout.strip(): print(f"  {SCRIPT_PREFIX}[STDOUT]: {e.stdout.strip()}")
        if e.stderr and e.stderr.strip(): print(f"  {SCRIPT_PREFIX}[STDERR]: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print(f"  {SCRIPT_PREFIX}[ERROR]: Command not found: {command_list[0]}. Is Python (o el comando) in your PATH?")
        return False
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}[ERROR]: Unexpected error executing command: {e}")
        return False

def main() -> bool:
    """Crea el entorno virtual si no existe."""
    # PROJECT_ROOT ya está definido globalmente en el script
    venv_path = PROJECT_ROOT / VENV_NAME

    print(f"{SCRIPT_PREFIX}--- Python Virtual Environment Creation ---")
    print(f"{SCRIPT_PREFIX}Project root: {PROJECT_ROOT}")

    python_executable_to_create_venv = sys.executable
    print(f"\n{SCRIPT_PREFIX}1. Using Python interpreter for venv creation: {python_executable_to_create_venv}")

    print(f"\n{SCRIPT_PREFIX}2. Checking/Creating virtual environment at: {venv_path}")
    if not venv_path.is_dir():
        print(f"   {SCRIPT_PREFIX}[INFO] Virtual environment directory not found. Creating...")
        if not run_command_for_venv([python_executable_to_create_venv, "-m", "venv", str(venv_path)], "Failed to create venv.", working_directory=str(PROJECT_ROOT)): # Especificar cwd
            return False
        print(f"   {SCRIPT_PREFIX}[OK] Virtual environment created at '{venv_path.relative_to(PROJECT_ROOT)}'.")
    else:
        print(f"   {SCRIPT_PREFIX}[INFO] Virtual environment directory '{venv_path.relative_to(PROJECT_ROOT)}' already exists. Skipping creation.")

    if os.name == 'nt':
        venv_python_exe_path = venv_path / "Scripts" / "python.exe"
        venv_activate_script_name = "activate.bat (CMD) or Activate.ps1 (PowerShell)"
    else:
        venv_python_exe_path = venv_path / "bin" / "python"
        venv_activate_script_name = "activate (Bash/Zsh)"

    if not venv_python_exe_path.is_file(): # Solo verificar python.exe/python es suficiente
        print(f"   {SCRIPT_PREFIX}[ERROR]: Virtual environment at '{venv_path.relative_to(PROJECT_ROOT)}' seems incomplete or corrupted.")
        print(f"                    (Expected python executable at: {venv_python_exe_path})")
        print(f"                    Consider deleting the '{VENV_NAME}' directory and re-running this script.")
        return False
    print(f"   {SCRIPT_PREFIX}[OK]: Virtual environment structure appears valid (found python executable).")

    print(f"\n{SCRIPT_PREFIX}--- Virtual Environment Creation Finished ---")
    print(f"{SCRIPT_PREFIX}Virtual environment '{VENV_NAME}' is ready (or already existed) at '{PROJECT_ROOT}'.")

    print(f"\n{SCRIPT_PREFIX}GUÍA: Para activar el entorno virtual en tu terminal actual, ejecuta:")
    if os.name == 'nt':
        print(f"  En CMD:          cd \"{PROJECT_ROOT}\" && {VENV_NAME}\\Scripts\\activate.bat")
        print(f"  En PowerShell:   cd \"{PROJECT_ROOT}\" ; .\\{VENV_NAME}\\Scripts\\Activate.ps1")
        print(f"                   (Puede que necesites ejecutar: Set-ExecutionPolicy Unrestricted -Scope Process)")
    else:
        print(f"  En Bash/Zsh:     cd \"{PROJECT_ROOT}\" && source ./{VENV_NAME}/bin/activate")
    print(f"\n{SCRIPT_PREFIX}El orquestador (s00_main_initial_setup.py) hará una pausa para que realices este paso.")
    print("-" * 60)

    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)