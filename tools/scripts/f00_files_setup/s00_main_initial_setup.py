# PROJECT_ROOT/tools/scripts/f00_files_setup/s00_main_initial_setup.py
import sys, os
from pathlib import Path

# MODIFICADO: Importaciones absolutas desde el paquete 'tools'
from tools.scripts.f00_files_setup import s01_create_structure as cs
from tools.scripts.f00_files_setup import s02_create_venv as cv
from tools.scripts.f00_files_setup import s03_setup_github_repo as sgr
from tools.scripts import utils_general as ug

# Constantes globales para el script
SCRIPT_PREFIX = "SCRIPT s00_main_initial_setup: "

def main():
    print(f"{SCRIPT_PREFIX}--- INICIANDO SETUP INICIAL (ESTRUCTURA, VENV, GITHUB) ---")
    project_root = ug.get_project_root()
    # Imprimir la raíz del proyecto detectada por utils_general para confirmación
    print(f"{SCRIPT_PREFIX}Raíz del proyecto según utils_general: {project_root}")


    # 1. Crear Estructura de Archivos y Carpetas (si no existen)
    print(f"\n{SCRIPT_PREFIX}PASO 1: Creando/Verificando estructura del proyecto...")
    if not cs.main():
        print(f"{SCRIPT_PREFIX}[ERROR] Falló la creación de la estructura.")
        sys.exit(1)

    # 2. Crear Entorno Virtual (si no existe)
    print(f"\n{SCRIPT_PREFIX}PASO 2: Creando/Verificando entorno virtual...")
    if not cv.main():
        print(f"{SCRIPT_PREFIX}[ERROR] Falló la creación del entorno virtual.")
        sys.exit(1)

    # Esta pausa es parte de tu flujo, así que la mantenemos.
    # La Guía de Configuración debe explicar claramente este paso manual.
    print(f"\n{SCRIPT_PREFIX}POR FAVOR, ACTIVA EL ENTORNO VIRTUAL ANTES DE CONTINUAR.")
    print(f"{SCRIPT_PREFIX}  El script hará una pausa. Abre otra terminal si es necesario,")
    print(f"{SCRIPT_PREFIX}  navega a la raíz del proyecto ('{project_root}') y activa el venv:")
    if os.name == 'nt':
        print(f"{SCRIPT_PREFIX}  En PowerShell: .\\.venv\\Scripts\\Activate.ps1")
        print(f"{SCRIPT_PREFIX}                (Puede que necesites ejecutar: Set-ExecutionPolicy Unrestricted -Scope Process)")
        print(f"{SCRIPT_PREFIX}  En CMD:        .venv\\Scripts\\activate.bat")
    else:
        print(f"{SCRIPT_PREFIX}  En Bash/Zsh:   source .venv/bin/activate")
    input(f"{SCRIPT_PREFIX}Presiona 'ENTER' DESPUÉS de haber activado el .venv para continuar...")


    # 3. Configurar Repositorio GitHub
    print(f"\n{SCRIPT_PREFIX}PASO 3: Configurando/Verificando repositorio GitHub...")
    if not sgr.main():
        print(f"{SCRIPT_PREFIX}[ERROR] Falló la configuración del repositorio GitHub.")
        print(f"{SCRIPT_PREFIX}              Revisa los mensajes de s03_setup_github_repo.py y la guía.")
        sys.exit(1)

    print(f"\n{SCRIPT_PREFIX}--- SCRIPT s00: SETUP INICIAL (ESTRUCTURA, VENV, GITHUB) COMPLETADO ---")
    print(f"{SCRIPT_PREFIX}[GUÍA]: El siguiente paso es configurar Google Cloud SDK (autenticación y proyecto) y luego instalar dependencias.")
    print(f"{SCRIPT_PREFIX}      Sigue las instrucciones de la 'Guía Definitiva de Configuración...' para la Fase 1.")

if __name__ == "__main__":
    # Asegurarnos de que el directorio raíz del proyecto (donde está 'tools') esté en sys.path
    # si este script se ejecuta directamente de una forma que no lo añade (ej. `python tools/scripts/.../script.py`)
    # Esto es crucial para que `from tools.scripts import ...` funcione.
    # Si se ejecuta con `python -m tools.scripts...`, la raíz ya está en sys.path.
    current_script_path = Path(__file__).resolve()
    # PROJECT_ROOT/tools/scripts/f00_files_setup/s00_main_initial_setup.py
    # Queremos PROJECT_ROOT en sys.path
    project_root_dir_for_import = current_script_path.parent.parent.parent.parent
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))

    main()