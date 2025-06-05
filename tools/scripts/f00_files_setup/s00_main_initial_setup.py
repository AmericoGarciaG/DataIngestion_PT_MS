# PROJECT_ROOT/scripts/f00_files_setup/s00_main_initial_setup.py
import sys
from pathlib import Path

# Importar módulos hermanos dentro del paquete 'setup'
from . import s01_create_structure as cs
from . import s02_create_venv as cv
from . import s03_setup_github_repo as sgr

def main():
    print("--- SCRIPT s00: INICIANDO SETUP INICIAL (ESTRUCTURA, VENV, GITHUB) ---")
    project_root = Path(__file__).resolve().parent.parent.parent
    print(f"SCRIPT s00: Raíz del proyecto detectada: {project_root}")

    # 1. Crear Estructura de Archivos y Carpetas (si no existen)
    print("\nSCRIPT s00: PASO 1: Creando/Verificando estructura del proyecto...")
    if not cs.main(): # Asumiendo que .main() devuelve True/False
        print("SCRIPT s00: ERROR: Falló la creación de la estructura.")
        sys.exit(1)

    # 2. Crear Entorno Virtual (si no existe)
    print("\nSCRIPT s00: PASO 2: Creando/Verificando entorno virtual...")
    if not cv.main(): # Asumiendo que .main() devuelve True/False
        print("SCRIPT s00: ERROR: Falló la creación del entorno virtual.")
        sys.exit(1)

    print("POR FAVOR, ACTIVA EL ENTORNO VIRTUAL ANTES DE CONTINUAR.")
    print("abre otra terminal y ejecuta los siguientes comandos (windows):")
    print(f"cd {project_root}")
    print("")
    print("Set-ExecutionPolicy Unrestricted -Scope Process")
    print("python -m venv .venv")
    print(".\\.venv\\Scripts\\activate")    
    input("Presiona 'ENTER' después de activar el .venv, para continuar con los siguientes pasos...")

    # 3. Configurar Repositorio GitHub
    # Este script (s03) ahora incluye la verificación de 'gh auth login' y guía al usuario si es necesario.
    print("\nSCRIPT s00: PASO 3: Configurando/Verificando repositorio GitHub...")
    if not sgr.main(): # s03_setup_github_repo.main()
        print("SCRIPT s00: ERROR: Falló la configuración del repositorio GitHub.")
        print("              Revisa los mensajes de s03_setup_github_repo.py y la guía.")
        sys.exit(1)

    print("\n--- SCRIPT s00: SETUP INICIAL (ESTRUCTURA, VENV, GITHUB) COMPLETADO ---")
    print("GUÍA: El siguiente paso es configurar Google Cloud SDK (autenticación y proyecto) y luego instalar dependencias.")
    print("      Sigue las instrucciones de la 'Guía Definitiva de Configuración...' para la Fase 1.")

if __name__ == "__main__":
    main() # El sys.exit(1) dentro de las llamadas a los submódulos o aquí si devuelven False.