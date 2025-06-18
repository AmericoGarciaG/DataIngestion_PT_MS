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

'''
# tools/scripts/f00_files_setup/s00_main_initial_setup.py

## 🎯 Propósito

Orquestar la configuración inicial completa del proyecto, incluyendo la creación de la estructura de directorios y archivos,
la configuración del entorno virtual (venv) y la inicialización del repositorio de GitHub.
Este script es el punto de partida para establecer un nuevo proyecto.

---

## ⚙️ Funcionamiento Principal

Este script ejecuta una secuencia de pasos para configurar el entorno del proyecto:

1.  **Obtención de la Raíz del Proyecto**: Utiliza `utils_general.get_project_root()` para determinar y mostrar la ruta raíz del proyecto.
2.  **Creación de Estructura (`s01_create_structure.main()`**)
    *   Llama al script `s01_create_structure.py` para generar la estructura de carpetas y archivos iniciales según se define en `tools/project_map.json`.
    *   Si este paso falla, el script principal termina.
3.  **Creación de Entorno Virtual (`s02_create_venv.main()`**)
    *   Llama al script `s02_create_venv.py` para crear un entorno virtual (`.venv`) en la raíz del proyecto.
    *   Si este paso falla, el script principal termina.
4.  **Pausa para Activación Manual del venv**:
    *   El script se detiene y solicita al usuario que active manualmente el entorno virtual recién creado.
    *   Proporciona instrucciones específicas para Windows (PowerShell, CMD) y sistemas basados en Unix (Bash/Zsh).
    *   Espera a que el usuario presione 'ENTER' para continuar.
5.  **Configuración de Repositorio GitHub (`s03_setup_github_repo.main()`**)
    *   Llama al script `s03_setup_github_repo.py` para inicializar un repositorio Git, configurar el `.gitignore`, crear un commit inicial y (opcionalmente) configurar un remote de GitHub.
    *   Si este paso falla, el script principal termina con un mensaje de error.
6.  **Mensaje de Finalización**: Informa al usuario que el setup inicial ha concluido y sugiere los siguientes pasos según la guía de configuración del proyecto.

El script está diseñado para ser ejecutado una vez al inicio de un nuevo proyecto o para asegurar que la configuración base esté correcta.

---

## ▶️ Uso

Este script está diseñado para ser ejecutado directamente desde la línea de comandos.

**Prerrequisitos**:
*   Ninguno, ya que este es el primer script a ejecutar en la configuración del proyecto.
*   Python 3 instalado.

**Ejecución**:
Navegar al directorio `PROJECT_ROOT` y ejecutar:
```bash
python tools/scripts/f00_files_setup/s00_main_initial_setup.py
```
o, si `tools` es reconocido como paquete (por ejemplo, si `PROJECT_ROOT` está en `PYTHONPATH` o se usa `-m`):
```bash
python -m tools.scripts.f00_files_setup.s00_main_initial_setup
```

El script se encarga de ajustar `sys.path` si es necesario para que las importaciones relativas al paquete `tools` funcionen correctamente cuando se ejecuta directamente.

---

## 🧩 Dependencias

*   **Módulos del proyecto `tools.scripts.f00_files_setup`**:
    *   `s01_create_structure` (alias `cs`): Para crear la estructura de directorios y archivos.
    *   `s02_create_venv` (alias `cv`): Para crear el entorno virtual.
    *   `s03_setup_github_repo` (alias `sgr`): Para configurar el repositorio Git/GitHub.
*   **Módulos del proyecto `tools.scripts`**:
    *   `utils_general` (alias `ug`): Para funciones de utilidad general, como obtener la raíz del proyecto.
*   **Módulos estándar de Python**:
    *   `sys`
    *   `os`
    *   `pathlib.Path`

---

## 📤 Salidas y Efectos Secundarios

*   **Creación de Estructura**: Genera directorios y archivos placeholder en el sistema de archivos.
*   **Creación de Entorno Virtual**: Crea una carpeta `.venv` con el entorno virtual de Python en la raíz del proyecto.
*   **Configuración de Git**:
    *   Inicializa un repositorio Git (`.git` carpeta).
    *   Crea o actualiza el archivo `.gitignore`.
    *   Realiza un commit inicial.
    *   Puede configurar un remote de GitHub si el usuario lo desea y proporciona la URL.
*   **Mensajes en Consola**: Imprime el progreso, instrucciones y mensajes de error/éxito en la consola.
*   **Modificación de `sys.path`**: Temporalmente añade la raíz del proyecto a `sys.path` si es necesario para las importaciones.
*   **Interrupción del Script**: El script termina (`sys.exit(1)`) si alguno de los pasos críticos (creación de estructura, venv, setup de GitHub) falla.
*   **Pausa para Interacción del Usuario**: El script se detiene esperando que el usuario active el venv.

---

## ✅ Buenas Prácticas y Consideraciones

*   **Idempotencia Parcial**: Los scripts subordinados (`s01`, `s02`, `s03`) intentan ser idempotentes (p.ej., no fallan si la estructura o el venv ya existen). Este script principal se beneficia de ello.
*   **Interactividad**: La pausa para la activación del venv es crucial para asegurar que los pasos subsecuentes (que podrían depender de herramientas instaladas en el venv) funcionen correctamente en el flujo general de setup.
*   **Modularidad**: Separa cada tarea principal (estructura, venv, git) en su propio script, lo que hace el proceso más manejable y fácil de depurar.
*   **Manejo de Errores**: Verifica el resultado de cada script subordinado y termina si hay un error crítico.
*   **Instrucciones Claras**: Proporciona información útil al usuario, incluyendo comandos para activar el venv.
---
'''