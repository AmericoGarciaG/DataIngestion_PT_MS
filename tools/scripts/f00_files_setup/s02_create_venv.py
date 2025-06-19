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

'''
# tools/scripts/f00_files_setup/s02_create_venv.py

## 🎯 Propósito

Crear y validar un entorno virtual de Python (denominado `.venv`) en la raíz del proyecto.
Este script asegura que el proyecto tenga un entorno aislado para sus dependencias, promoviendo
la reproducibilidad y evitando conflictos entre paquetes de diferentes proyectos.

---

## ⚙️ Funcionamiento Principal

1.  **Determinación de Rutas**:
    *   Obtiene la ruta raíz del proyecto utilizando `utils_general.get_project_root()`.
    *   Define el nombre del directorio del entorno virtual (`.venv`).

2.  **Selección del Intérprete de Python**:
    *   Utiliza el ejecutable de Python que está corriendo el propio script (`sys.executable`) para crear el entorno virtual. Esto garantiza la consistencia si múltiples versiones de Python están instaladas en el sistema.

3.  **Creación del Entorno Virtual**:
    *   Verifica si el directorio `.venv` ya existe en la raíz del proyecto.
    *   Si no existe:
        *   Informa al usuario que se procederá con la creación.
        *   Ejecuta el comando `python -m venv .venv` (utilizando el `sys.executable` previamente determinado) en el directorio raíz del proyecto.
        *   La función `run_command_for_venv` (una utilidad interna de este script) gestiona la ejecución del comando, captura de salida y manejo de errores.
        *   Si la creación falla, el script termina informando un error.
    *   Si el directorio `.venv` ya existe, se informa al usuario y se omite la creación.

4.  **Validación de la Estructura del Entorno Virtual**:
    *   Comprueba la existencia del ejecutable de Python dentro del entorno virtual recién creado (o existente).
        *   En Windows: `.venv/Scripts/python.exe`
        *   En otros sistemas (Linux/macOS): `.venv/bin/python`
    *   Si no se encuentra el ejecutable, se considera que el entorno virtual está incompleto o corrupto, se informa un error y se sugiere eliminar el directorio `.venv` y reintentar.

5.  **Mensajes Finales**:
    *   Informa que el entorno virtual está listo (o ya existía).
    *   Indica que el script principal (`s00_main_initial_setup.py`) guiará al usuario sobre cómo activar el venv y los siguientes pasos.

La función `main()` del script devuelve `True` si todas las operaciones fueron exitosas, o `False` en caso de error. El bloque `if __name__ == "__main__":` asegura que el script termine con un código de salida `1` si `main()` reporta un fallo.

---

## ▶️ Uso

Este script está diseñado principalmente para ser llamado por el script orquestador `s00_main_initial_setup.py`.
Sin embargo, también puede ser ejecutado directamente si se desea crear (o recrear) únicamente el entorno virtual.

**Prerrequisitos**:
*   Python 3 instalado y accesible a través del comando `python` (o el ejecutable que corre el script).
*   El módulo `venv` debe estar disponible en la instalación de Python (generalmente lo está por defecto).

**Ejecución directa**:
Desde la raíz del proyecto (`PROJECT_ROOT`):
```bash
python tools/scripts/f00_files_setup/s02_create_venv.py
```
o
```bash
python -m tools.scripts.f00_files_setup.s02_create_venv
```

---

## 🧩 Dependencias

*   **Módulos del proyecto `tools.scripts`**:
    *   `utils_general` (alias `ug`): Para obtener la ruta raíz del proyecto (`get_project_root()`).
*   **Módulos estándar de Python**:
    *   `os`: Para manipulación de rutas y nombres de sistema operativo (`os.name`).
    *   `subprocess`: Para ejecutar comandos externos (como `python -m venv`).
    *   `sys`: Para acceder al ejecutable de Python actual (`sys.executable`) y para `sys.exit()`.
    *   `pathlib`: Para manipulación de rutas de forma orientada a objetos.

---

## 📤 Salidas y Efectos Secundarios

*   **Creación de Directorio `.venv`**: Si no existe, crea un directorio llamado `.venv` en la raíz del proyecto, conteniendo la estructura del entorno virtual de Python.
*   **Mensajes en Consola**: Imprime información sobre el proceso, incluyendo:
    *   La ruta del intérprete de Python utilizado.
    *   El estado de la creación del venv (creando, omitiendo si ya existe).
    *   Resultados de la validación del venv.
    *   Mensajes de error detallados si ocurren problemas.
*   **Código de Salida**: El script termina con `sys.exit(1)` si la creación o validación del venv falla cuando se ejecuta directamente.

---

## ✅ Buenas Prácticas y Consideraciones

*   **Uso de `sys.executable`**: Asegura que el venv se cree con la misma versión de Python que ejecuta el script, lo cual es fundamental para la consistencia.
*   **Idempotencia**: El script verifica si el directorio `.venv` ya existe y omite la creación si es así, permitiendo ejecuciones repetidas sin errores.
*   **Validación Básica**: Comprueba la existencia del ejecutable de Python dentro del venv como una forma simple de verificar que la creación fue, al menos parcialmente, exitosa.
*   **Manejo de Errores**: Utiliza `try-except` y verifica códigos de retorno de `subprocess` para informar errores de manera clara.
*   **Claridad en los Mensajes**: Informa al usuario sobre las acciones que se están tomando y los resultados.
---
'''