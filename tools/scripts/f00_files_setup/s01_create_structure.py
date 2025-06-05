# PROJECT_ROOT/tools/scripts/f00_files_setup/s01_create_structure.py
import pathlib
import sys
import json # Para cargar el project_map.json

# Constantes globales para el script
SCRIPT_FILE_PATH = pathlib.Path(__file__).resolve()
# Asumimos que este script está en Project_Root/tools/scripts/f00_files_setup/
PROJECT_ROOT = SCRIPT_FILE_PATH.parent.parent.parent.parent
SCRIPT_PREFIX = "SCRIPT s01: "

# Ruta al archivo project_map.json (asumiendo que está en tools/)
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
    else:
        print(f"  {SCRIPT_PREFIX}[SKIP] Directory already exists: {path_to_log}")
    
    if success and create_init:
        init_py = path / "__init__.py"
        init_py_to_log = init_py.relative_to(PROJECT_ROOT) if init_py.is_absolute() else init_py
        if not init_py.exists():
            try:
                init_py.touch()
                print(f"  {SCRIPT_PREFIX}[OK] Created file: {init_py_to_log}")
            except Exception as e:
                print(f"  {SCRIPT_PREFIX}ERROR: Failed to create __init__.py in {path_to_log}. Error: {e}")
                success = False
    return success


def create_file_if_not_exists(path: pathlib.Path, content: str | None = None) -> bool:
    """Crea un archivo si no existe. Opcionalmente con contenido inicial."""
    path_to_log = path.relative_to(PROJECT_ROOT) if path.is_absolute() else path
    if not path.exists():
        try:
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
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
    # ... (función get_input_simple como la tenías) ...
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

    if project_map_data:
        # ETAPA 1: Crear directorios definidos en project_map.json
        print(f"\n{SCRIPT_PREFIX}ETAPA 1: Creando directorios definidos en 'project_map.json'...")
        if "directories_to_create" in project_map_data and project_map_data["directories_to_create"]:
            for dir_relative_path_str in project_map_data["directories_to_create"]:
                # Determinar si se debe crear __init__.py
                # Regla simple: si el directorio está bajo 'app', 'scripts', o 'tests' y no es un sub-subdirectorio como '_restore' o '__pycache__'
                create_init = False
                path_parts = pathlib.Path(dir_relative_path_str).parts
                if path_parts:
                    if path_parts[0] in ["app", "scripts", "tests"]:
                        # Para scripts, solo en el primer nivel de subcarpetas
                        if path_parts[0] == "scripts" and len(path_parts) == 2 and not path_parts[1].startswith("__"):
                             create_init = True
                        elif path_parts[0] != "scripts" and not path_parts[-1].startswith("__"): # Para app y tests
                             create_init = True
                    # Excepción para .docs/_restore y otros directorios especiales
                    if "_restore" in path_parts or ".devcontainer" in path_parts or ".vscode" in path_parts or ".github" in path_parts :
                        create_init = False


                if not create_dir_if_not_exists(PROJECT_ROOT / dir_relative_path_str, create_init):
                    all_successful = False
        else:
            print(f"{SCRIPT_PREFIX}ADVERTENCIA: No se encontró la sección 'directories_to_create' en '{PROJECT_MAP_JSON_PATH.name}' o está vacía.")

        if not all_successful:
            print(f"{SCRIPT_PREFIX}ETAPA 1 finalizada CON ERRORES en la creación de directorios. No se crearán archivos placeholder.")
            return False
        print(f"{SCRIPT_PREFIX}ETAPA 1 (Creación de Directorios) completada.")
        print("-" * 60)

        # ETAPA 2: Crear archivos placeholder definidos en project_map.json (con confirmación)
        continue_stage2 = get_input_simple(f"\n{SCRIPT_PREFIX}¿Deseas crear archivos placeholder basados en 'project_map.json' (Etapa 2)?")
        if continue_stage2 == 'n':
            print(f"{SCRIPT_PREFIX}Creación de archivos placeholder (Etapa 2) omitida por el usuario.")
        else:
            print(f"\n{SCRIPT_PREFIX}ETAPA 2: Creando archivos placeholder definidos en 'project_map.json'...")
            if "file_mappings" in project_map_data and project_map_data["file_mappings"]:
                for backup_file_key, destination_relative_path_str in project_map_data["file_mappings"].items():
                    # backup_file_key es el nombre en BckUp_Files/
                    # destination_relative_path_str es el path de destino incluyendo el nombre final del archivo
                    
                    target_file_path = PROJECT_ROOT / destination_relative_path_str
                    
                    # Evitar que el script se cree a sí mismo si está en el mapa
                    if target_file_path.resolve() == SCRIPT_FILE_PATH:
                        print(f"  {SCRIPT_PREFIX}[SKIP] Self-creation (listado en project_map.json): {target_file_path.relative_to(PROJECT_ROOT)}")
                        continue
                    
                    # Contenido placeholder genérico
                    placeholder_content = f"# Placeholder para: {target_file_path.relative_to(PROJECT_ROOT)}\n# (Este archivo sería restaurado desde BckUp_Files/{backup_file_key} por _restore_files.ps1)\n"
                    if target_file_path.name == "__init__.py":
                        placeholder_content = "" # Los __init__.py pueden estar vacíos

                    if not create_file_if_not_exists(target_file_path, placeholder_content):
                        all_successful = False
            else:
                print(f"{SCRIPT_PREFIX}ADVERTENCIA: No se encontró la sección 'file_mappings' en '{PROJECT_MAP_JSON_PATH.name}' o está vacía.")
            
            if not all_successful: # Re-chequear después de crear archivos
                print(f"{SCRIPT_PREFIX}ETAPA 2 finalizada CON ERRORES en la creación de archivos placeholder.")
                return False
            print(f"{SCRIPT_PREFIX}ETAPA 2 (Creación de Archivos Placeholder) completada.")

    else: # project_map_data no se pudo cargar
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo cargar '{PROJECT_MAP_JSON_PATH.name}'. La estructura no se creará/verificará completamente desde el mapa.")
        # Aquí podrías tener una estructura mínima por defecto si el JSON falla, o simplemente salir.
        # Por ahora, si el JSON falla, el script no hará mucho más.
        all_successful = False # Considerar esto un fallo si el JSON es esencial.

    print("-" * 60)
    if all_successful:
        print(f"{SCRIPT_PREFIX}Proceso de creación/verificación de estructura finalizado exitosamente.")
        return True
    else:
        print(f"{SCRIPT_PREFIX}Proceso de creación/verificación de estructura finalizado CON ERRORES.")
        return False

if __name__ == "__main__":
    if not main():
        sys.exit(1)