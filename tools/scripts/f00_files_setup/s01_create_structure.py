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