# PROJECT_ROOT/tools/scripts/f00_files_setup/s01_create_structure.py
import pathlib
import sys
import json # Para cargar el project_map.json

# Asegúrate de que esta importación sea la correcta para tu estructura final.
# Si ejecutas este script como parte de un paquete más grande (ej. `python -m tools.scripts...`)
# y utils_general.py está en `tools/scripts/`, entonces la siguiente es correcta:
from .. import utils_general as ug
# Si ejecutas este script directamente y utils_general.py está en `tools/scripts/`,
# necesitarías ajustar sys.path aquí o usar una importación diferente.
# Por ahora, asumo que la estructura de ejecución principal lo maneja.


# Constantes globales para el script
SCRIPT_FILE_PATH = pathlib.Path(__file__).resolve()
PROJECT_ROOT = ug.get_project_root() # Utilizar la función get_project_root()
SCRIPT_PREFIX = "SCRIPT s01: " # Prefijo para mensajes de log
# Ruta al archivo project_map.json
PROJECT_MAP_JSON_PATH = PROJECT_ROOT / "tools" / "project_map.json"


def create_dir_if_not_exists(path: pathlib.Path, create_init: bool = False) -> bool:
    """Crea un directorio si no existe. Opcionalmente crea un __init__.py dentro."""
    success = True
    path_to_log = path.relative_to(PROJECT_ROOT) if path.is_absolute() else path
    if not path.exists():
        try:
            path.mkdir(parents=True, exist_ok=True)
            print(f"  {SCRIPT_PREFIX}[OK] Created directory: {path_to_log}")
        except Exception as e:
            print(f"  {SCRIPT_PREFIX}ERROR: Failed to create directory {path_to_log}. Error: {e}")
            success = False
    # No imprimimos "SKIP" aquí si ya existe, la lógica principal maneja el flujo
    
    if success and create_init: # Solo intenta crear __init__.py si el dir se creó o ya existía y se requiere
        init_py = path / "__init__.py"
        init_py_to_log = init_py.relative_to(PROJECT_ROOT) if init_py.is_absolute() else init_py
        if not init_py.exists():
            try:
                init_py.touch()
                print(f"  {SCRIPT_PREFIX}[OK] Created file: {init_py_to_log}")
            except Exception as e:
                print(f"  {SCRIPT_PREFIX}ERROR: Failed to create __init__.py in {path_to_log}. Error: {e}")
                success = False # Marcar como fallo si no se pudo crear el __init__ requerido
    return success


def create_file_if_not_exists(path: pathlib.Path, content: str | None = None) -> bool:
    """Crea un archivo si no existe. Opcionalmente con contenido inicial."""
    path_to_log = path.relative_to(PROJECT_ROOT) if path.is_absolute() else path
    if not path.exists():
        try:
            # Asegurar que el directorio padre exista ANTES de crear el archivo
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                parent_to_log = path.parent.relative_to(PROJECT_ROOT) if path.parent.is_absolute() else path.parent
                print(f"  {SCRIPT_PREFIX}[INFO] Implicitly created parent directory: {parent_to_log} for file {path_to_log}")

            with open(path, 'w', encoding='utf-8') as f:
                if content is None: # Contenido por defecto si no se provee
                    content = f"# Placeholder for {path_to_log}\n"
                f.write(content)
            print(f"  {SCRIPT_PREFIX}[OK] Created file: {path_to_log}")
        except Exception as e:
            print(f"  {SCRIPT_PREFIX}ERROR: Failed to create file {path_to_log}. Error: {e}")
            return False
    else:
        print(f"  {SCRIPT_PREFIX}[SKIP] File already exists: {path_to_log}")
    return True

def get_input_simple(prompt: str, default: str = 's') -> str:
    """Obtiene un input simple (s/n) del usuario."""
    while True:
        response = input(f"{prompt} (S/n, default: {default}): ").strip().lower()
        if not response: return default
        if response in ['s', 'n']: return response
        print("Respuesta inválida. Por favor, ingresa 's' o 'n'.")


def load_project_map() -> dict | None:
    """Carga la estructura del proyecto desde project_map.json."""
    print(f"{SCRIPT_PREFIX}Cargando mapa de proyecto desde: {PROJECT_MAP_JSON_PATH.relative_to(PROJECT_ROOT)}")
    if not PROJECT_MAP_JSON_PATH.is_file():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo '{PROJECT_MAP_JSON_PATH.name}' no encontrado en la ubicación esperada.")
        print(f"                Se intentará crear una estructura mínima sin el mapa.")
        return None
    try:
        with open(PROJECT_MAP_JSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"{SCRIPT_PREFIX}ERROR: Falló el parseo de JSON en '{PROJECT_MAP_JSON_PATH.name}': {e}")
    except Exception as e:
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo leer '{PROJECT_MAP_JSON_PATH.name}': {e}")
    return None


def main() -> bool:
    """Crea la estructura de carpetas y archivos para el proyecto."""
    print(f"{SCRIPT_PREFIX}--- Creando/Verificando Estructura del Proyecto ---")
    print(f"{SCRIPT_PREFIX}Raíz del Proyecto: {PROJECT_ROOT}")
    print("-" * 60)

    all_successful = True
    project_map_data = load_project_map()

    if not project_map_data:
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo cargar '{PROJECT_MAP_JSON_PATH.name}'. "
              "La estructura no se creará/verificará completamente desde el mapa.")
        return False

    # --- Determinar directorios necesarios y crearlos ---
    print(f"\n{SCRIPT_PREFIX}Verificando y creando directorios necesarios...")
    
    dirs_with_content_or_ancestors = set()
    files_to_create_map = project_map_data.get("file_mappings", {})
    
    if files_to_create_map:
        for _, destination_relative_path_str in files_to_create_map.items():
            file_path = pathlib.Path(destination_relative_path_str)
            current_parent = file_path.parent
            # Añadir el directorio padre del archivo y todos sus ancestros
            while current_parent and str(current_parent) != '.': # Evitar añadir '.' como directorio
                dirs_with_content_or_ancestors.add(str(current_parent))
                current_parent = current_parent.parent
    
    directories_to_explicitly_create = project_map_data.get("directories_to_create", [])
    # Combinar los directorios explícitos con los inferidos de los archivos
    all_potential_dirs_str = set(directories_to_explicitly_create).union(dirs_with_content_or_ancestors)
    
    # Ordenar para ayudar a crear padres antes que hijos (aunque mkdir -p lo maneja)
    sorted_target_dirs_str = sorted(list(all_potential_dirs_str), key=lambda p: len(pathlib.Path(p).parts))
    created_dirs_this_run_paths = set() # Para llevar registro de qué directorios se crearon/modificaron en ESTA ejecución

    for dir_relative_path_str in sorted_target_dirs_str:
        dir_path_obj = PROJECT_ROOT / dir_relative_path_str
        
        # Determinar si se debe crear __init__.py
        create_init = False
        path_parts = pathlib.Path(dir_relative_path_str).parts
        if path_parts: # Asegurar que path_parts no esté vacío
            # Lógica simplificada para __init__.py (ajusta según tus necesidades)
            # Crear __init__.py si es un subdirectorio directo de 'tools/scripts', 'service/app', 'service/tests'
            # y no es un directorio especial como __pycache__
            if len(path_parts) > 1 and not path_parts[-1].startswith(("_", ".")): # Ignorar __pycache__, .venv, etc.
                # Para tools/scripts/fXX_...
                if path_parts[0] == "tools" and len(path_parts) > 1 and path_parts[1] == "scripts" and len(path_parts) == 3:
                    create_init = True
                # Para service/app y service/tests
                elif path_parts[0] == "service" and len(path_parts) > 1 and path_parts[1] in ["app", "tests"] and len(path_parts) == 2:
                    create_init = True
                # Añade aquí más reglas si "app/" directamente bajo tools/ o la raíz debe ser paquete, etc.

            # Excepciones específicas para no crear __init__.py
            if "_restore" in path_parts or ".devcontainer" in path_parts or ".vscode" in path_parts or ".github" in path_parts:
                create_init = False

        # Intenta crear el directorio (si no existe) y/o el __init__.py (si se requiere y no existe)
        if not create_dir_if_not_exists(dir_path_obj, create_init):
            all_successful = False
        # Si create_dir_if_not_exists fue True, significa que o el dir se creó, o ya existía,
        # y si se requería __init__.py, o se creó o ya existía.
        # No necesitamos añadir a created_dirs_this_run_paths aquí a menos que queramos un log muy específico.
    
    # Informar sobre directorios explícitamente listados que no se crearon (y no existen)
    # porque se determinó que estarían vacíos y no son ancestros necesarios.
    for dir_in_map_str in directories_to_explicitly_create:
        dir_in_map_path = PROJECT_ROOT / dir_in_map_str
        # Se omite si: no es un ancestro necesario Y no está en la lista de los que sí se procesaron Y realmente no existe
        if dir_in_map_str not in dirs_with_content_or_ancestors and \
           dir_in_map_str not in sorted_target_dirs_str and \
           not dir_in_map_path.exists():
            print(f"  {SCRIPT_PREFIX}[INFO] Omitida creación del directorio (explícito pero vacío y no ancestro): {dir_in_map_str}")
    
    if not all_successful:
        print(f"{SCRIPT_PREFIX}Proceso finalizado CON ERRORES durante la creación de directorios.")
        return False
    print(f"{SCRIPT_PREFIX}Creación/verificación de directorios completada.")
    print("-" * 60)

    # --- Crear archivos placeholder (con confirmación única) ---
    if not files_to_create_map:
        print(f"{SCRIPT_PREFIX}No hay 'file_mappings' definidos en '{PROJECT_MAP_JSON_PATH.name}'. "
              "No se crearán archivos placeholder.")
    else:
        continue_file_creation = get_input_simple(f"\n{SCRIPT_PREFIX}¿Deseas crear archivos placeholder basados en 'project_map.json'?")
        if continue_file_creation == 'n':
            print(f"{SCRIPT_PREFIX}Creación de archivos placeholder omitida por el usuario.")
        else:
            print(f"\n{SCRIPT_PREFIX}Creando archivos placeholder definidos en 'project_map.json'...")
            for backup_file_key, destination_relative_path_str in files_to_create_map.items():
                target_file_path = PROJECT_ROOT / destination_relative_path_str
                
                if target_file_path.resolve() == SCRIPT_FILE_PATH: # Evitar que el script se cree a sí mismo
                    print(f"  {SCRIPT_PREFIX}[SKIP] Self-creation (listado en project_map.json): {target_file_path.relative_to(PROJECT_ROOT)}")
                    continue
                
                placeholder_content = f"# Placeholder para: {target_file_path.relative_to(PROJECT_ROOT)}\n# (Este archivo sería restaurado desde BckUp_Files/{backup_file_key} por _restore_files.ps1)\n"
                if target_file_path.name == "__init__.py":
                    placeholder_content = "" # Los __init__.py pueden estar vacíos

                if not create_file_if_not_exists(target_file_path, placeholder_content):
                    all_successful = False
            
            if not all_successful: # Re-chequear después de crear archivos
                print(f"{SCRIPT_PREFIX}Proceso finalizado CON ERRORES durante la creación de archivos placeholder.")
                return False
            print(f"{SCRIPT_PREFIX}Creación de archivos placeholder completada.")

    print("-" * 60)
    if all_successful:
        print(f"{SCRIPT_PREFIX}Proceso de creación/verificación de estructura finalizado exitosamente.")
        return True
    else:
        # El mensaje de error específico ya se habrá impreso
        return False

if __name__ == "__main__":
    if not main():
        sys.exit(1)

'''
# tools/scripts/f00_files_setup/s01_create_structure.py

## 🎯 Propósito

Crear la estructura inicial de directorios y archivos para el proyecto, basándose en la configuración definida
en el archivo `tools/project_map.json`. Este script asegura que todos los directorios necesarios existan
y que los archivos placeholder (o archivos `__init__.py` para paquetes) estén en su lugar.

---

## ⚙️ Funcionamiento Principal

El script opera de la siguiente manera:

1.  **Carga del Mapa del Proyecto**:
    *   Lee el archivo `PROJECT_ROOT/tools/project_map.json`. Este archivo JSON contiene dos claves principales:
        *   `directories_to_create`: Una lista de rutas de directorios (relativas a `PROJECT_ROOT`) que deben ser creados explícitamente.
        *   `file_mappings`: Un diccionario donde las claves son identificadores (posiblemente para un futuro sistema de backup/restore) y los valores son las rutas de archivos (relativas a `PROJECT_ROOT`) que deben ser creados.
    *   Si `project_map.json` no se encuentra o no es válido, el script emite un error y no puede crear la estructura basada en el mapa.

2.  **Creación de Directorios**:
    *   Identifica todos los directorios que necesitan ser creados. Esto incluye:
        *   Directorios listados explícitamente en `directories_to_create`.
        *   Directorios padre de todos los archivos listados en `file_mappings`.
    *   Los directorios se ordenan por profundidad para intentar crear los padres antes que los hijos.
    *   Para cada directorio:
        *   Se verifica si ya existe. Si no, se crea usando `pathlib.Path.mkdir(parents=True, exist_ok=True)`.
        *   **Creación de `__init__.py`**: Se determina si se debe crear un archivo `__init__.py` en el directorio para tratarlo como un paquete. La lógica actual es:
            *   Si el directorio es un subdirectorio directo de `tools/scripts` (ej. `tools/scripts/fXX_...`), `service/app`, o `service/tests`.
            *   Se pueden añadir más reglas o excepciones (ej. no crear en `.vscode`, `__pycache__`).
            *   Si `__init__.py` es requerido y no existe, se crea.
    *   Se informa sobre directorios que estaban en `directories_to_create` pero se omitieron por estar vacíos y no ser ancestros de ningún archivo.

3.  **Creación de Archivos Placeholder**:
    *   Si `file_mappings` existe en `project_map.json`, el script pregunta al usuario si desea continuar con la creación de archivos.
    *   Si el usuario confirma:
        *   Para cada archivo en `file_mappings`:
            *   Se verifica si ya existe. Si no:
                *   Se asegura que el directorio padre del archivo exista (creándolo si es necesario).
                *   Se crea el archivo.
                *   Se escribe un contenido placeholder por defecto (ej. `# Placeholder para: ruta/del/archivo`), a menos que el archivo sea `__init__.py`, en cuyo caso se deja vacío.
            *   Se omite la auto-creación si el script actual está listado en el mapa.
    *   Si la creación de algún archivo o directorio falla, se marca un indicador de error.

4.  **Resultado**:
    *   El script imprime un resumen indicando si el proceso fue exitoso o si ocurrieron errores.
    *   Devuelve `True` si todas las operaciones fueron exitosas, `False` en caso contrario. La función `main()` del script termina con `sys.exit(1)` si esta función devuelve `False`.

El script utiliza `utils_general.get_project_root()` para determinar la raíz del proyecto y construye todas las rutas de forma relativa a esta raíz.

---

## ▶️ Uso

Este script está diseñado para ser ejecutado directamente, usualmente como parte de un script de setup más grande (como `s00_main_initial_setup.py`), pero también puede ejecutarse individualmente para regenerar o verificar la estructura.

**Prerrequisitos**:
*   El archivo `tools/project_map.json` debe existir en la ubicación esperada (`PROJECT_ROOT/tools/project_map.json`) y ser un JSON válido con la estructura esperada.
*   Python 3.

**Ejecución**:
Desde la raíz del proyecto (`PROJECT_ROOT`):
```bash
python tools/scripts/f00_files_setup/s01_create_structure.py
```
o
```bash
python -m tools.scripts.f00_files_setup.s01_create_structure
```

---

## 🧩 Dependencias

*   **Módulos del proyecto `tools.scripts`**:
    *   `utils_general` (alias `ug`): Para obtener la ruta raíz del proyecto (`get_project_root()`).
*   **Módulos estándar de Python**:
    *   `pathlib`: Para manipulación de rutas de forma orientada a objetos.
    *   `sys`: Para `sys.exit()`.
    *   `json`: Para cargar y parsear `project_map.json`.

---

## 📥 Entradas

*   **`tools/project_map.json`**: Archivo JSON que define la estructura de directorios y la lista de archivos placeholder a crear. Debe contener:
    *   `directories_to_create` (lista de strings): Rutas de directorios a crear.
    *   `file_mappings` (diccionario): Mapeo de claves a rutas de archivos a crear.
    *   Ejemplo de `project_map.json`:
        ```json
        {
          "directories_to_create": [
            "docs",
            "data/raw",
            "service/app",
            "service/tests"
          ],
          "file_mappings": {
            "README_md": "README.md",
            "main_py": "service/app/main.py",
            "init_app_py": "service/app/__init__.py",
            "gitignore": ".gitignore"
          }
        }
        ```

---

## 📤 Salidas y Efectos Secundarios

*   **Creación/Modificación del Sistema de Archivos**:
    *   Crea directorios especificados si no existen.
    *   Crea archivos `__init__.py` en los directorios de paquetes si no existen.
    *   Crea archivos placeholder con contenido básico si no existen.
*   **Mensajes en Consola**: Imprime logs detallados sobre cada operación (creación, omisión, error) y un resumen final.
*   **Código de Salida**: El script principal (`if __name__ == "__main__":`) termina con `sys.exit(1)` si la función `main()` devuelve `False` (indicando un error).

---

## ✅ Buenas Prácticas y Consideraciones

*   **Importancia de `project_map.json`**: Este archivo es la "fuente de verdad" para la estructura del proyecto. Mantenerlo actualizado es crucial.
*   **Idempotencia**: El script está diseñado para ser idempotente. Si se ejecuta múltiples veces, no debería fallar ni causar problemas; simplemente omitirá la creación de directorios/archivos que ya existan.
*   **Contenido Placeholder**: El contenido por defecto de los archivos creados es mínimo. Para archivos `__init__.py`, se crean vacíos.
*   **Manejo de Errores**: El script intenta capturar excepciones durante operaciones de sistema de archivos e informa sobre ellas.
*   **Modularidad de `__init__.py`**: La lógica para decidir dónde crear `__init__.py` está centralizada y puede ser ajustada según las convenciones del proyecto para definir qué directorios son paquetes.
*   **Confirmación del Usuario**: La creación de archivos placeholder requiere una confirmación del usuario (S/n) para evitar la creación accidental de muchos archivos si no se desea.
---
'''