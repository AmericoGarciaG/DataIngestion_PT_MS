# PROJECT_ROOT/scripts/f00_files_setup/s03_setup_github_repo.py
import os
import subprocess
import sys
import shutil
import pathlib

# Importar desde el paquete padre 'scripts'
from ..utils_general import get_project_root, run_command_in_dir, get_input

# Constantes globales para el script
SCRIPT_PREFIX = "SCRIPT s03_github: " # Cambiado para diferenciar de s01, s02
VENV_DIR_NAME = ".venv" # Nombre del directorio del entorno virtual

def check_gh_cli_installed() -> bool:
    """Verifica si la CLI de GitHub ('gh') está instalada y autenticada."""
    print(f"{SCRIPT_PREFIX}Verificando instalacion y autenticacion de GitHub CLI ('gh')...")
    project_root_dir = get_project_root() 

    if not run_command_in_dir(["gh", "--version"], str(project_root_dir), exit_on_error=False, suppress_stdout_if_captured=True):
        print(f"  {SCRIPT_PREFIX}ERROR: GitHub CLI ('gh') no encontrada o no ejecutable.")
        print("         Por favor, instálala desde https://cli.github.com/")
        return False
    # print(f"  {SCRIPT_PREFIX}[INFO] gh CLI es ejecutable.") # Ya lo imprime run_command_in_dir
    
    gh_exe = shutil.which("gh.exe") if os.name == 'nt' else shutil.which("gh")
    if not gh_exe:
        print(f"  {SCRIPT_PREFIX}ERROR: Ejecutable de gh no encontrado en PATH para 'auth status'.")
        return False
        
    auth_status_command = [gh_exe, "auth", "status"]
    use_shell_for_auth = (os.name == 'nt')
    auth_cmd_arg_for_subprocess = subprocess.list2cmdline(auth_status_command) if use_shell_for_auth else auth_status_command
    
    try:
        auth_status_result = subprocess.run(
            auth_cmd_arg_for_subprocess, capture_output=True, text=True, check=False, 
            shell=use_shell_for_auth, encoding="utf-8", errors="replace"
        )
        if auth_status_result.returncode == 0 and "Logged in to github.com" in auth_status_result.stdout:
            print(f"  {SCRIPT_PREFIX}[OK] GitHub CLI instalada y usuario autenticado.")
            return True
        else:
            print(f"  {SCRIPT_PREFIX}ERROR: GitHub CLI instalada pero no autenticada, o error al verificar.")
            # ... (resto de los prints de error como los tenías) ...
            if auth_status_result.stdout and auth_status_result.stdout.strip(): print(f"    STDOUT de 'gh auth status':\n{auth_status_result.stdout.strip()}")
            if auth_status_result.stderr and auth_status_result.stderr.strip(): print(f"    STDERR de 'gh auth status':\n{auth_status_result.stderr.strip()}")
            print(f"  {SCRIPT_PREFIX}GUÍA: Por favor, ejecuta 'gh auth login' manualmente y luego vuelve a ejecutar este script.")
            return False
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR ejecutando 'gh auth status': {e}")
        return False

def ensure_gitignore_rules(project_root: pathlib.Path, rules: list[str]) -> bool:
    """Asegura que las reglas especificadas estén en .gitignore."""
    gitignore_path = project_root / ".gitignore"
    new_rules_added = False
    content_to_write = []
    
    if gitignore_path.exists():
        print(f"  {SCRIPT_PREFIX}[INFO] Leyendo .gitignore existente: {gitignore_path.relative_to(project_root)}")
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            existing_rules = [line.strip() for line in f.readlines()]
        content_to_write.extend(existing_rules)
    else:
        print(f"  {SCRIPT_PREFIX}[INFO] .gitignore no encontrado. Se creará uno nuevo.")
        existing_rules = []

    for rule in rules:
        if rule not in existing_rules:
            print(f"    {SCRIPT_PREFIX}[NEW] Añadiendo regla '{rule}' a .gitignore.")
            content_to_write.append(rule)
            new_rules_added = True
        else:
            print(f"    {SCRIPT_PREFIX}[SKIP] Regla '{rule}' ya existe en .gitignore.")

    if new_rules_added:
        try:
            # Añadir un salto de línea al final si el archivo no estaba vacío y no termina con uno
            if content_to_write and content_to_write[-1] != "" and len(content_to_write) > len(existing_rules):
                 content_to_write.insert(len(existing_rules) if existing_rules else 0, "") # Espacio antes de nuevas reglas

            # Asegurar que haya un salto de línea al final del archivo
            if content_to_write and content_to_write[-1]:
                 content_to_write.append("")

            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(content_to_write))
            print(f"  {SCRIPT_PREFIX}[OK] .gitignore actualizado en: {gitignore_path.relative_to(project_root)}")
        except Exception as e:
            print(f"  {SCRIPT_PREFIX}ERROR: Falló al escribir en .gitignore: {e}")
            return False
    return True


def main() -> bool:
    """Configura el repositorio Git local y el repositorio remoto en GitHub."""
    print(f"{SCRIPT_PREFIX}--- Iniciando Configuración de Repositorio Git y GitHub ---")
    project_root = get_project_root()
    print(f"{SCRIPT_PREFIX}Raíz del proyecto detectada: {project_root}")

    if not check_gh_cli_installed():
        return False 

    # --- 1. Inicializar Git Localmente (si no se ha hecho) ---
    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio Git local no encontrado. Inicializando...")
        if not run_command_in_dir(["git", "init"], str(project_root)): return False
        if not run_command_in_dir(["git", "branch", "-M", "main"], str(project_root)): return False
        print(f"{SCRIPT_PREFIX}[OK] Repositorio Git local inicializado y rama principal 'main'.")
    else:
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio Git local ya existe en '{git_dir}'.")
        run_command_in_dir(["git", "branch", "-M", "main"], str(project_root), exit_on_error=False)

    # --- 2. Asegurar que .gitignore tenga .env y VENV_DIR_NAME ---
    print(f"\n{SCRIPT_PREFIX}Asegurando reglas en .gitignore...")
    rules_to_ignore = [".env", f"{VENV_DIR_NAME}/"] # VENV_DIR_NAME usualmente es ".venv"
    if not ensure_gitignore_rules(project_root, rules_to_ignore):
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo actualizar .gitignore. Abortando para prevenir commit de archivos sensibles.")
        return False

    # --- 3. Obtener OWNER y REPO_NAME ---
    # (Lógica para obtener repo_owner y repo_name_final como la tenías,
    #  quizás leyendo defaults de .env si python-dotenv está disponible y .env existe)
    from dotenv import load_dotenv # Cargar para leer defaults
    env_path = project_root / ".env"
    if env_path.is_file(): load_dotenv(env_path)

    default_repo_name_only = project_root.name
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name_final = os.getenv("GITHUB_REPO_NAME")

    if not repo_owner or not repo_name_final:
        print(f"{SCRIPT_PREFIX}[INFO] GITHUB_REPO_OWNER y/o GITHUB_REPO_NAME no en .env. Se solicitarán.")
        repo_input_prompt = (f"{SCRIPT_PREFIX}Nombre para repositorio GitHub (default: {default_repo_name_only}, puede ser 'OWNER/NOMBRE'):")
        repo_name_input = get_input(repo_input_prompt, default_repo_name_only)
        if not repo_name_input: print(f"{SCRIPT_PREFIX}[ERROR]: Nombre de repositorio requerido."); return False
        if '/' in repo_name_input:
            owner_in, name_in = repo_name_input.split('/', 1)
            if not repo_owner: repo_owner = owner_in
            if not repo_name_final: repo_name_final = name_in
        else:
            if not repo_name_final: repo_name_final = repo_name_input
            if not repo_owner: # Solo si no vino de .env
                try:
                    # ... (lógica de detección de owner con gh api user) ...
                    gh_executable = shutil.which("gh.exe") if os.name == 'nt' else shutil.which("gh")
                    if gh_executable:
                        gh_api_command = [gh_executable, "api", "user", "-q", ".login"]
                        user_info_result = subprocess.run(gh_api_command, capture_output=True, text=True, check=True, shell=(os.name == 'nt'))
                        detected_owner = user_info_result.stdout.strip()
                        if detected_owner:
                            print(f"{SCRIPT_PREFIX}Usuario de GitHub detectado: {detected_owner}")
                            if get_input(f"{SCRIPT_PREFIX}Usar '{detected_owner}' como propietario? (S/n)", "S").lower() == 's':
                                repo_owner = detected_owner
                except Exception: pass # Ignorar errores de detección, se pedirá manualmente
            if not repo_owner: # Aún no hay owner
                repo_owner = get_input(f"{SCRIPT_PREFIX}Ingresa el OWNER (usuario/org) de GitHub para '{repo_name_final}':")
    
    if not repo_owner or not repo_name_final:
        print(f"{SCRIPT_PREFIX}[ERROR]: Owner o nombre del repo no determinados."); return False
    full_repo_name_gh = f"{repo_owner}/{repo_name_final}"
    print(f"{SCRIPT_PREFIX}Configurando para el repositorio GitHub: {full_repo_name_gh}")

    # --- 4. Asegurar que haya al menos un commit ---
    # (Lógica de git rev-parse, git add ., git commit como la tenías)
    has_commits = False
    try:
        subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=project_root, check=True, capture_output=True, text=True, errors="ignore")
        has_commits = True
        print(f"{SCRIPT_PREFIX}[INFO] Ya existen commits en el repositorio local.")
    except subprocess.CalledProcessError:
        print(f"{SCRIPT_PREFIX}[INFO] No hay commits. Creando commit inicial...")
        if not run_command_in_dir(["git", "add", "."], str(project_root)): return False
        commit_msg = "Fase 0: Estructura inicial y scripts de setup base"
        if not run_command_in_dir(["git", "commit", "-m", commit_msg], str(project_root), exit_on_error=False):
            print(f"{SCRIPT_PREFIX}[INFO] No se realizó commit inicial (quizás no había archivos nuevos para commitear).")
        else:
            print(f"{SCRIPT_PREFIX}[OK] Commit inicial creado: '{commit_msg}'.")
            has_commits = True

    # --- 5. Verificar/Crear Repositorio Remoto y Configurar Remoto Local ---
    # (Lógica de gh repo view, gh repo create, git remote add/set-url como la tenías)
    print(f"\n{SCRIPT_PREFIX}Verificando/Creando repositorio remoto '{full_repo_name_gh}' en GitHub...")
    # ... (resto de la lógica igual que en tu última versión, con los prefijos SCRIPT s03:) ...
    repo_exists_remotely = run_command_in_dir(["gh", "repo", "view", full_repo_name_gh], str(project_root), exit_on_error=False, suppress_stdout_if_captured=True)
    remote_url_expected = f"https://github.com/{full_repo_name_gh}.git"

    if not repo_exists_remotely:
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio remoto '{full_repo_name_gh}' no existe. Intentando crear...")
        # ... (get_input para description, visibility) ...
        repo_description = get_input(f"{SCRIPT_PREFIX}Descripción para el repositorio (opcional):", f"Proyecto {repo_name_final}")
        visibility_choice = get_input(f"{SCRIPT_PREFIX}Visibilidad (public/private/internal, default: private):", "private", r"^(public|private|internal)$").lower()
        create_command = ["gh", "repo", "create", full_repo_name_gh, f"--{visibility_choice}"]
        if repo_description: create_command.extend(["--description", repo_description])
        create_command.extend(["--source=.", "--remote=origin"]) # NO --push aquí todavía
        if not run_command_in_dir(create_command, str(project_root), pass_through_stdio=True):
            print(f"{SCRIPT_PREFIX}[ERROR] No se pudo crear repositorio remoto."); return False
        print(f"{SCRIPT_PREFIX}[OK] Repositorio remoto '{full_repo_name_gh}' creado y remoto 'origin' configurado.")
    else: # Repo ya existe
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio remoto '{full_repo_name_gh}' ya existe.")
        # ... (lógica de verificar/setear remote url) ...
        # (Esta parte de tu script anterior era bastante buena)
        git_remote_get_url_cmd = ["git", "remote", "get-url", "origin"]
        proc_get_url = subprocess.run(git_remote_get_url_cmd, cwd=project_root, capture_output=True, text=True, check=False)
        origin_url_current = proc_get_url.stdout.strip() if proc_get_url.returncode == 0 else None
        if origin_url_current == remote_url_expected: print(f"{SCRIPT_PREFIX}[OK] Remoto 'origin' ya configurado.")
        elif origin_url_current:
            print(f"{SCRIPT_PREFIX}ADVERTENCIA: Remoto 'origin' apunta a '{origin_url_current}'. Actualizando.")
            if not run_command_in_dir(["git", "remote", "set-url", "origin", remote_url_expected], str(project_root)): return False
        else: 
            print(f"{SCRIPT_PREFIX}[INFO] Remoto 'origin' no encontrado. Añadiéndolo.")
            if not run_command_in_dir(["git", "remote", "add", "origin", remote_url_expected], str(project_root)): return False


    # --- 6. Hacer Push a GitHub (si hay commits) ---
    if has_commits:
        print(f"\n{SCRIPT_PREFIX}Intentando hacer push de la rama 'main' a 'origin'...")
        if not run_command_in_dir(["git", "push", "-u", "origin", "main", "--force"], str(project_root), pass_through_stdio=True, exit_on_error=False): # Añadido --force
            print(f"{SCRIPT_PREFIX}ADVERTENCIA: Falló el push. Revisa la salida. Podrías necesitar 'git pull' o resolver conflictos.")
            # No retornamos False aquí necesariamente, el repo y remoto están configurados.
        else:
            print(f"{SCRIPT_PREFIX}[OK] Push a origin/main exitoso o rama ya actualizada.")
    else:
        print(f"{SCRIPT_PREFIX}[INFO] No hay commits locales para hacer push.")


    print(f"\n{SCRIPT_PREFIX}--- Configuración de Repositorio GitHub Finalizada ---")
    print(f"{SCRIPT_PREFIX}Puedes acceder a tu repositorio en: https://github.com/{full_repo_name_gh}")

    print(f"\n{SCRIPT_PREFIX}[INFO]: NEXT STEP: Populate 'requirements.txt' and then run 'pip install -r requirements.txt' from an activated venv.")
    print("-" * 60)
    return True

if __name__ == "__main__":
    if not main():
        sys.exit(1)





