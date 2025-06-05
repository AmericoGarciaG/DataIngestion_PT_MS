# PROJECT_ROOT/scripts/utils_general.py
import os
import subprocess
import sys
import pathlib
import re 
import shutil
import time # Para find_available_resource_suffix
import json # Para _check_wif_pool_exists_in_gcp (si parsea JSON)

def get_project_root() -> pathlib.Path:
    """Determina la raíz del proyecto desde la ubicación de este script."""
    return pathlib.Path(__file__).resolve().parent.parent.parent

def run_command_in_dir(command_list, working_directory, exit_on_error=True, env_vars=None, pass_through_stdio=False, suppress_stdout_if_captured=False):
    """Ejecuta un comando en un directorio específico y maneja la salida."""
    effective_command_list = list(command_list)
    command_name_to_find = effective_command_list[0]
    is_windows = (os.name == 'nt')
    executable_path_found = None

    if is_windows:
        if command_name_to_find.lower() == "gcloud": executable_path_found = shutil.which("gcloud.cmd")
        elif command_name_to_find.lower() == "terraform": executable_path_found = shutil.which("terraform.exe")
        elif command_name_to_find.lower() == "gh": executable_path_found = shutil.which("gh.exe")
        elif command_name_to_find.lower() == "git": executable_path_found = shutil.which("git.exe")
    
    if not executable_path_found: executable_path_found = shutil.which(command_name_to_find)

    if not executable_path_found:
        print(f"UTILS: ERROR: Comando '{command_name_to_find}' no encontrado en PATH.")
        if exit_on_error: sys.exit(1)
        return False
    
    effective_command_list[0] = executable_path_found
    use_shell = is_windows
    command_str_for_display = ' '.join(effective_command_list)

    # print(f"DEBUG: utils_general.py: Original command list: {command_list}")
    # print(f"DEBUG: utils_general.py: Executable path found: {executable_path_found}")
    # print(f"DEBUG: utils_general.py: Effective command list: {effective_command_list}")
    # print(f"DEBUG: utils_general.py: Will use shell={use_shell}")
    
    print(f"\nUTILS: --- Ejecutando en '{working_directory}': {command_str_for_display} ---")
    
    current_env = os.environ.copy()
    if env_vars: current_env.update(env_vars)
    
    command_arg_for_subprocess = subprocess.list2cmdline(effective_command_list) if use_shell else effective_command_list
    # if use_shell: print(f"DEBUG: utils_general.py: Cmd as string for shell=True: {command_arg_for_subprocess}")

    kwargs_subprocess = {"cwd": str(working_directory), "check": False, "env": current_env, "shell": use_shell}
    if not pass_through_stdio:
        kwargs_subprocess.update({"capture_output": True, "text": True})
        if is_windows: kwargs_subprocess.update({"encoding": "utf-8", "errors": "replace"})

    try:
        process = subprocess.run(command_arg_for_subprocess, **kwargs_subprocess)
        if not pass_through_stdio:
            stdout_content = process.stdout.strip() if process.stdout else ""
            stderr_content = process.stderr.strip() if process.stderr else ""
            if stdout_content and not suppress_stdout_if_captured: print(f"UTILS: --- STDOUT ---\n{stdout_content}")
            if stderr_content: print(f"UTILS: --- {'STDERR (comando falló)' if process.returncode != 0 else 'INFO (desde stderr)'} ---\n{stderr_content}")
        
        if process.returncode != 0:
            print(f"UTILS: ERROR: Comando '{command_str_for_display}' falló con código {process.returncode}")
            if exit_on_error: sys.exit(process.returncode)
            return False
        return True
    except FileNotFoundError:
        print(f"UTILS: ERROR CRÍTICO: FileNotFoundError DESPUÉS de que shutil.which encontró: '{executable_path_found}'.")
        if exit_on_error: sys.exit(1)
        return False
    except Exception as e:
        print(f"UTILS: ERROR inesperado ejecutando '{command_str_for_display}': {e}")
        if exit_on_error: sys.exit(1)
        return False

def get_gcloud_project_config():
    """Obtiene el Project ID configurado localmente en gcloud."""
    gcloud_exe = shutil.which("gcloud.cmd") if os.name == 'nt' else shutil.which("gcloud")
    if not gcloud_exe: return None
    try:
        cmd = [gcloud_exe, "config", "get-value", "project"]
        use_shell = (os.name == 'nt')
        cmd_arg = subprocess.list2cmdline(cmd) if use_shell else cmd
        result = subprocess.run(cmd_arg, capture_output=True, text=True, check=False, shell=use_shell, encoding="utf-8", errors="replace")
        if result.returncode == 0:
            project_id = result.stdout.strip()
            if project_id and project_id != "(unset)": return project_id
    except Exception: pass
    return None

def get_input(prompt_message, default_value=None, validator_regex=None, validation_message="Entrada invalida."):
    # ... (sin cambios) ...
    while True:
        if default_value is not None:
            prompt_message_full = f"{prompt_message} (default: {default_value}): "
        else:
            prompt_message_full = f"{prompt_message}: "
        value = input(prompt_message_full).strip()
        if not value and default_value is not None: return default_value
        if value:
            if validator_regex:
                if re.fullmatch(validator_regex, value): return value
                else: print(f"ERROR: {validation_message} (Debe coincidir con: {validator_regex})")
            else: return value
        elif not value and default_value is None: print("ERROR: Este campo es requerido.")


def _check_wif_pool_exists_in_gcp(pool_id_to_check: str, gcp_project_id: str) -> bool:
    """Verifica si un Workload Identity Pool existe. True si existe, False si no o hay error."""
    print(f"    UTILS: Verificando existencia de WIF Pool '{pool_id_to_check}' en proyecto '{gcp_project_id}'...")
    if not gcp_project_id:
        print(f"    UTILS: ERROR (_check_wif_pool_exists): gcp_project_id no fue proporcionado.")
        return True # Asumir que existe para no bloquear, el error real es la falta de project_id

    gcloud_exe = shutil.which("gcloud.cmd") if os.name == 'nt' else shutil.which("gcloud")
    if not gcloud_exe:
        print(f"    UTILS: ERROR (_check_wif_pool_exists): gcloud CLI no encontrada.")
        return True # Asumir que existe si gcloud no está, problema de setup mayor

    cmd = [gcloud_exe, "iam", "workload-identity-pools", "describe", pool_id_to_check,
           "--project", gcp_project_id, "--location=global", "--format=value(name)"]
    use_shell = (os.name == 'nt')
    cmd_arg = subprocess.list2cmdline(cmd) if use_shell else cmd
    try:
        proc = subprocess.run(cmd_arg, capture_output=True, text=True, shell=use_shell, check=False, encoding="utf-8", errors="replace")
        # 'describe' tiene éxito (returncode 0) si el pool existe (incluso soft-deleted).
        if proc.returncode == 0 and proc.stdout.strip():
            print(f"    UTILS: [INFO] WIF Pool '{pool_id_to_check}' encontrado.")
            return True 
        # print(f"    DEBUG (_check_wif_pool_exists): Pool '{pool_id_to_check}' no encontrado. RC: {proc.returncode}, Stderr: {proc.stderr.strip()}")
        return False 
    except Exception as e:
        print(f"    UTILS: ERROR (_check_wif_pool_exists): Excepción al verificar pool '{pool_id_to_check}': {e}")
        return True # En error inesperado, asumir que existe para no entrar en bucle infinito.

def find_available_resource_suffix(base_name: str, start_suffix_int: int, max_attempts: int,
                                     check_existence_func, suffix_format_zeros: int = 3,
                                     *check_func_args) -> str | None:
    """Encuentra un sufijo numérico disponible. Devuelve el sufijo formateado o None."""
    print(f"UTILS: Buscando sufijo disponible para '{base_name}', inicio: {start_suffix_int:0{suffix_format_zeros}}...")
    current_suffix_val = start_suffix_int
    for attempt in range(max_attempts):
        formatted_suffix = str(current_suffix_val).zfill(suffix_format_zeros)
        name_to_try = f"{base_name}-{formatted_suffix}"
        
        print(f"  UTILS: Intento {attempt + 1}/{max_attempts}: Verificando '{name_to_try}'...")
        if not check_existence_func(name_to_try, *check_func_args):
            print(f"  UTILS: [OK] Sufijo '{formatted_suffix}' disponible. Nombre final: '{name_to_try}'")
            return formatted_suffix
        
        print(f"  UTILS: [INFO] '{name_to_try}' ya existe o no está disponible.")
        current_suffix_val += 1
        if attempt < max_attempts - 1: time.sleep(0.2) # Pequeña pausa

    print(f"UTILS: ERROR: No se pudo encontrar sufijo disponible para '{base_name}' tras {max_attempts} intentos.")
    return None