# PROJECT_ROOT/tools/scripts/f00_files_setup/s03_setup_github_repo.py
import os
import subprocess
import sys
import shutil
import pathlib

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

# Constantes globales para el script
SCRIPT_PREFIX = "SCRIPT s03_github: "
VENV_DIR_NAME = ".venv"

def check_gh_cli_installed() -> bool:
    """Verifica si la CLI de GitHub ('gh') está instalada y autenticada."""
    print(f"{SCRIPT_PREFIX}Verificando instalacion y autenticacion de GitHub CLI ('gh')...")
    project_root_dir = ug.get_project_root()

    # Primero, verificar si 'gh' es ejecutable y está en PATH usando run_command_in_dir
    # Esto ya imprime mensajes útiles si el comando no se encuentra.
    if not ug.run_command_in_dir(["gh", "--version"], str(project_root_dir), exit_on_error=False, suppress_stdout_if_captured=True):
        print(f"  {SCRIPT_PREFIX}ERROR: GitHub CLI ('gh') no encontrada o no ejecutable.")
        print(f"         Por favor, instálala desde https://cli.github.com/ y asegúrate de que esté en tu PATH.")
        return False
    print(f"  {SCRIPT_PREFIX}[INFO] 'gh --version' ejecutado exitosamente (gh CLI está disponible).")

    # Luego, específicamente verificar el estado de autenticación
    gh_exe = shutil.which("gh.exe") if os.name == 'nt' else shutil.which("gh")
    if not gh_exe:
        # Esto no debería ocurrir si el paso anterior tuvo éxito, pero es una doble verificación.
        print(f"  {SCRIPT_PREFIX}ERROR CRÍTICO: Ejecutable de gh no encontrado en PATH después de la verificación inicial.")
        return False

    auth_status_command = [gh_exe, "auth", "status"]
    use_shell_for_auth = (os.name == 'nt')
    auth_cmd_arg_for_subprocess = subprocess.list2cmdline(auth_status_command) if use_shell_for_auth else auth_status_command

    try:
        # Ejecutar 'gh auth status' para verificar la autenticación
        # Usamos subprocess.run directamente aquí porque run_command_in_dir podría salir si exit_on_error=True
        # y necesitamos manejar la salida de 'gh auth status' más específicamente.
        print(f"  {SCRIPT_PREFIX}Ejecutando: {' '.join(auth_status_command)}")
        auth_status_result = subprocess.run(
            auth_cmd_arg_for_subprocess, capture_output=True, text=True, check=False,
            shell=use_shell_for_auth, encoding="utf-8", errors="replace"
        )

        # Imprimir stdout y stderr para depuración si es necesario, incluso en éxito aparente
        # if auth_status_result.stdout and auth_status_result.stdout.strip():
        #     print(f"    DEBUG STDOUT de 'gh auth status':\n{auth_status_result.stdout.strip()}")
        # if auth_status_result.stderr and auth_status_result.stderr.strip() and "Logged in to github.com" not in auth_status_result.stderr : # No mostrar stderr si solo es el mensaje de login
        #     print(f"    DEBUG STDERR de 'gh auth status':\n{auth_status_result.stderr.strip()}")


        # gh auth status devuelve 0 si está logueado, 1 si no.
        # El mensaje "Logged in to github.com" puede estar en stdout o stderr.
        if auth_status_result.returncode == 0 and \
           ("Logged in to github.com" in auth_status_result.stdout or \
            "Logged in to github.com" in auth_status_result.stderr):
            print(f"  {SCRIPT_PREFIX}[OK] GitHub CLI instalada y usuario autenticado.")
            return True
        else:
            print(f"  {SCRIPT_PREFIX}ERROR: GitHub CLI no autenticada o error al verificar estado.")
            if auth_status_result.stdout and auth_status_result.stdout.strip():
                 print(f"    STDOUT de 'gh auth status':\n{auth_status_result.stdout.strip()}")
            if auth_status_result.stderr and auth_status_result.stderr.strip():
                 print(f"    STDERR de 'gh auth status':\n{auth_status_result.stderr.strip()}")
            print(f"  {SCRIPT_PREFIX}GUÍA: Por favor, ejecuta 'gh auth login' manualmente en una terminal y luego vuelve a ejecutar este script.")
            return False
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR inesperado ejecutando 'gh auth status': {e}")
        return False

def ensure_gitignore_rules(project_root: pathlib.Path, rules: list[str]) -> bool:
    """Asegura que las reglas especificadas estén en .gitignore."""
    gitignore_path = project_root / ".gitignore"
    new_rules_added = False
    current_content_lines = []

    if gitignore_path.exists():
        print(f"  {SCRIPT_PREFIX}[INFO] Leyendo .gitignore existente: {gitignore_path.relative_to(project_root)}")
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            current_content_lines = [line.strip() for line in f.readlines()]
    else:
        print(f"  {SCRIPT_PREFIX}[INFO] .gitignore no encontrado. Se creará uno nuevo.")

    # Usar una copia para modificar y luego comparar
    updated_content_lines = list(current_content_lines)

    for rule in rules:
        if rule not in updated_content_lines: # Verificar contra la lista actual que se está construyendo
            print(f"    {SCRIPT_PREFIX}[NEW] Añadiendo regla '{rule}' a .gitignore.")
            # Añadir un espacio antes de las nuevas reglas si el archivo ya tiene contenido
            if updated_content_lines and not new_rules_added: # Solo la primera vez que se añade algo nuevo
                if updated_content_lines[-1] != "": # Si la última línea no es vacía
                    updated_content_lines.append("") # Añadir un separador
            updated_content_lines.append(rule)
            new_rules_added = True
        else:
            print(f"    {SCRIPT_PREFIX}[SKIP] Regla '{rule}' ya existe en .gitignore.")

    if new_rules_added:
        # Asegurar un salto de línea al final si el archivo no está vacío
        if updated_content_lines and updated_content_lines[-1]:
             updated_content_lines.append("")
        try:
            with open(gitignore_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(updated_content_lines)) # Escribir líneas con saltos
            print(f"  {SCRIPT_PREFIX}[OK] .gitignore actualizado en: {gitignore_path.relative_to(project_root)}")
        except Exception as e:
            print(f"  {SCRIPT_PREFIX}ERROR: Falló al escribir en .gitignore: {e}")
            return False
    return True


def main() -> bool:
    """Configura el repositorio Git local y el repositorio remoto en GitHub."""
    print(f"{SCRIPT_PREFIX}--- Iniciando Configuración de Repositorio Git y GitHub ---")
    project_root = ug.get_project_root()
    print(f"{SCRIPT_PREFIX}Raíz del proyecto detectada: {project_root}")

    if not check_gh_cli_installed():
        return False

    # --- 1. Inicializar Git Localmente (si no se ha hecho) ---
    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio Git local no encontrado. Inicializando...")
        if not ug.run_command_in_dir(["git", "init"], str(project_root)): return False
        # Es buena práctica establecer la rama principal a 'main' inmediatamente
        if not ug.run_command_in_dir(["git", "branch", "-M", "main"], str(project_root)): return False
        print(f"{SCRIPT_PREFIX}[OK] Repositorio Git local inicializado y rama principal establecida a 'main'.")
    else:
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio Git local ya existe en '{git_dir}'.")
        # Asegurar que la rama principal sea 'main' incluso si el repo ya existe
        ug.run_command_in_dir(["git", "branch", "-M", "main"], str(project_root), exit_on_error=False)


    # --- 2. Asegurar que .gitignore tenga .env y VENV_DIR_NAME ---
    print(f"\n{SCRIPT_PREFIX}Asegurando reglas en .gitignore...")
    # Asegúrate de que .env esté en .gitignore ANTES de cualquier commit.
    # El orden en que se añaden las reglas no importa funcionalmente, pero sí estéticamente.
    rules_to_ignore = [
        ".env",             # Archivos de entorno locales
        "service/.env",     # Si tienes .env específicos de servicio
        f"{VENV_DIR_NAME}/", # Directorio del entorno virtual
        "__pycache__/",     # Cache de Python
        "*.pyc",            # Archivos compilados de Python
        ".DS_Store",        # Archivos de metadatos de macOS
        "build/",           # Directorios de build
        "dist/",            # Directorios de distribución
        "*.egg-info/",      # Metadatos de setuptools
        "terraform/.terraform/", # Directorio de estado local de Terraform
        "terraform/terraform.tfstate*", # Archivos de estado de Terraform (si no usas backend remoto)
        "terraform/tfplan.out", # Archivos de plan de Terraform
        ".vscode/",         # Configuraciones de VSCode específicas del usuario (si no son compartidas)
                            # Si launch.json, settings.json son compartidos, no los ignores aquí.
    ]
    if not ensure_gitignore_rules(project_root, rules_to_ignore):
        print(f"{SCRIPT_PREFIX}ERROR: No se pudo actualizar .gitignore. Abortando para prevenir commit de archivos sensibles.")
        return False

    # --- 3. Obtener OWNER y REPO_NAME ---
    try:
        from dotenv import load_dotenv
        env_path_service = project_root / "service" / ".env" # Preferir el .env de service si existe
        env_path_root = project_root / ".env" # Fallback al .env de la raíz

        loaded_env_path = None
        if env_path_service.is_file():
            load_dotenv(env_path_service)
            loaded_env_path = env_path_service
        elif env_path_root.is_file():
            load_dotenv(env_path_root)
            loaded_env_path = env_path_root

        if loaded_env_path:
            print(f"{SCRIPT_PREFIX}[INFO] Variables de entorno cargadas desde: {loaded_env_path.relative_to(project_root)}")
        else:
            print(f"{SCRIPT_PREFIX}[INFO] No se encontró archivo .env en 'service/' ni en la raíz del proyecto. Se solicitarán todas las entradas para GitHub.")
    except ImportError:
        print(f"{SCRIPT_PREFIX}[WARN] 'python-dotenv' no instalado. No se leerán variables de .env para defaults de GitHub.")


    default_repo_name_only = project_root.name # Nombre de la carpeta del proyecto
    repo_owner = os.getenv("GITHUB_REPO_OWNER")
    repo_name_final = os.getenv("GITHUB_REPO_NAME")

    if not repo_owner or not repo_name_final:
        print(f"{SCRIPT_PREFIX}[INFO] GITHUB_REPO_OWNER y/o GITHUB_REPO_NAME no encontrados como variables de entorno (o .env). Se solicitarán.")
        repo_input_prompt = (f"{SCRIPT_PREFIX}Nombre para el repositorio GitHub (default: {default_repo_name_only}, o ingresa 'OWNER/NOMBRE_REPO'):")
        repo_name_input = ug.get_input(repo_input_prompt, default_repo_name_only)
        if not repo_name_input: print(f"{SCRIPT_PREFIX}ERROR: Nombre de repositorio es requerido."); return False

        if '/' in repo_name_input: # Si el usuario ingresó "OWNER/REPO"
            owner_in, name_in = repo_name_input.split('/', 1)
            if not repo_owner: repo_owner = owner_in.strip()
            if not repo_name_final: repo_name_final = name_in.strip()
        else: # Si el usuario solo ingresó el nombre del repo
            if not repo_name_final: repo_name_final = repo_name_input.strip()
            # Intentar detectar owner si no se proveyó y no estaba en .env
            if not repo_owner:
                try:
                    gh_executable = shutil.which("gh.exe") if os.name == 'nt' else shutil.which("gh")
                    if gh_executable:
                        # gh api user -q .login es más directo que gh auth status para obtener el login
                        gh_api_command = [gh_executable, "api", "user", "-q", ".login"]
                        user_info_result = subprocess.run(gh_api_command, capture_output=True, text=True, check=True, shell=(os.name == 'nt'), encoding="utf-8", errors="replace")
                        detected_owner = user_info_result.stdout.strip()
                        if detected_owner:
                            print(f"  {SCRIPT_PREFIX}Usuario de GitHub autenticado detectado: {detected_owner}")
                            if ug.get_input(f"  {SCRIPT_PREFIX}¿Usar '{detected_owner}' como propietario del repositorio? (S/n)", "S").lower() == 's':
                                repo_owner = detected_owner
                except Exception as e_gh_user:
                    print(f"  {SCRIPT_PREFIX}[WARN] No se pudo detectar automáticamente el propietario de GitHub: {e_gh_user}. Se solicitará manualmente.")
            if not repo_owner: # Si aún no hay owner, solicitarlo
                repo_owner = ug.get_input(f"{SCRIPT_PREFIX}Ingresa el PROPIETARIO (usuario/organización) de GitHub para el repositorio '{repo_name_final}':")
                if not repo_owner: print(f"{SCRIPT_PREFIX}ERROR: Propietario de GitHub es requerido."); return False
                repo_owner = repo_owner.strip()

    if not repo_owner or not repo_name_final:
        print(f"{SCRIPT_PREFIX}ERROR: Propietario o nombre del repositorio no pudieron ser determinados."); return False
    full_repo_name_gh = f"{repo_owner}/{repo_name_final}"
    print(f"{SCRIPT_PREFIX}Configurando para el repositorio GitHub: {full_repo_name_gh}")

    # --- 4. Asegurar que haya al menos un commit ---
    has_commits = False
    try:
        # Verificar si HEAD existe (lo que implica al menos un commit)
        subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=project_root, check=True, capture_output=True, text=True, errors="ignore")
        has_commits = True
        print(f"{SCRIPT_PREFIX}[INFO] Ya existen commits en el repositorio local.")
    except subprocess.CalledProcessError:
        print(f"{SCRIPT_PREFIX}[INFO] No hay commits. Creando commit inicial...")
        if not ug.run_command_in_dir(["git", "add", "."], str(project_root)): return False
        commit_msg = "Fase 0: Estructura inicial y scripts de setup base"
        # Permitir que el commit falle si no hay nada que commitear (ej. si .gitignore cubre todo lo nuevo)
        if not ug.run_command_in_dir(["git", "commit", "-m", commit_msg], str(project_root), exit_on_error=False):
            print(f"  {SCRIPT_PREFIX}[INFO] No se realizó commit inicial (quizás no había archivos nuevos o modificados para commitear después de aplicar .gitignore).")
            # Verificar de nuevo si ahora hay commits (ej. si 'git add .' sí añadió algo que .gitignore no cubría)
            try:
                subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=project_root, check=True, capture_output=True, text=True, errors="ignore")
                has_commits = True
            except subprocess.CalledProcessError:
                has_commits = False # Sigue sin haber commits
        else:
            print(f"  {SCRIPT_PREFIX}[OK] Commit inicial creado: '{commit_msg}'.")
            has_commits = True

    # --- 5. Verificar/Crear Repositorio Remoto y Configurar Remoto Local ---
    print(f"\n{SCRIPT_PREFIX}Verificando/Creando repositorio remoto '{full_repo_name_gh}' en GitHub...")
    # También es común usar SSH: remote_url_expected_ssh = f"git@github.com:{full_repo_name_gh}.git"
    repo_exists_remotely = ug.run_command_in_dir(["gh", "repo", "view", full_repo_name_gh], str(project_root), exit_on_error=False, suppress_stdout_if_captured=True)
    remote_url_expected = f"https://github.com/{full_repo_name_gh}.git" # Esta es la URL HTTPS correcta

    if not repo_exists_remotely:
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio remoto '{full_repo_name_gh}' no existe en GitHub. Intentando crear...")
        repo_description = ug.get_input(f"{SCRIPT_PREFIX}Descripción para el repositorio (opcional, default: Proyecto {repo_name_final}):", f"Proyecto {repo_name_final}")
        visibility_choice = ug.get_input(f"{SCRIPT_PREFIX}Visibilidad del repositorio (public/private/internal, default: private):", "private", r"^(public|private|internal)$").lower()
        
        create_command = ["gh", "repo", "create", full_repo_name_gh, f"--{visibility_choice}"]
        if repo_description: create_command.extend(["--description", repo_description])
        # --source=. : usa el directorio actual como fuente
        # --remote=origin : configura el remoto 'origin' automáticamente si se crea
        # NO --push aquí; haremos el push explícitamente después.
        create_command.extend(["--source=.", "--remote=origin"])
        
        if not ug.run_command_in_dir(create_command, str(project_root), pass_through_stdio=True): # pass_through para ver prompts de gh
            print(f"{SCRIPT_PREFIX}ERROR: No se pudo crear el repositorio remoto '{full_repo_name_gh}'.")
            return False
        print(f"{SCRIPT_PREFIX}[OK] Repositorio remoto '{full_repo_name_gh}' creado y remoto 'origin' configurado.")
    else: # Repo ya existe
        print(f"{SCRIPT_PREFIX}[INFO] Repositorio remoto '{full_repo_name_gh}' ya existe en GitHub.")
        # Verificar si el remoto 'origin' está configurado y apunta correctamente
        git_remote_get_url_cmd = ["git", "remote", "get-url", "origin"]
        proc_get_url = subprocess.run(git_remote_get_url_cmd, cwd=project_root, capture_output=True, text=True, check=False, encoding="utf-8", errors="replace")
        origin_url_current = proc_get_url.stdout.strip() if proc_get_url.returncode == 0 else None

        # --- INICIO DE CORRECCIÓN ---
        if origin_url_current == remote_url_expected: # Usar remote_url_expected
            print(f"{SCRIPT_PREFIX}[OK] Remoto 'origin' ya está configurado y apunta a '{remote_url_expected}'.") # Usar remote_url_expected
        elif origin_url_current: # Existe pero es diferente
            print(f"{SCRIPT_PREFIX}ADVERTENCIA: Remoto 'origin' apunta a '{origin_url_current}'. Se actualizará a '{remote_url_expected}'.") # Usar remote_url_expected
            if not ug.run_command_in_dir(["git", "remote", "set-url", "origin", remote_url_expected], str(project_root)): return False # Usar remote_url_expected
            print(f"{SCRIPT_PREFIX}[OK] Remoto 'origin' actualizado.")
        else: # No existe el remoto 'origin'
            print(f"{SCRIPT_PREFIX}[INFO] Remoto 'origin' no encontrado localmente. Añadiéndolo...")
            if not ug.run_command_in_dir(["git", "remote", "add", "origin", remote_url_expected], str(project_root)): return False # Usar remote_url_expected
            print(f"{SCRIPT_PREFIX}[OK] Remoto 'origin' añadido.")


    # --- 6. Hacer Push a GitHub (si hay commits y el remoto está configurado) ---
    if has_commits:
        print(f"\n{SCRIPT_PREFIX}Intentando hacer push de la rama 'main' a 'origin'...")
        # Usar --force-with-lease si es posible, o --force si es la primera configuración y sabes lo que haces.
        # Por simplicidad en un setup inicial, --force es común, pero advierte sobre ello.
        # Si el repo remoto está vacío, --force no es estrictamente necesario, pero -u sí es útil.
        if not ug.run_command_in_dir(["git", "push", "-u", "origin", "main"], str(project_root), pass_through_stdio=True, exit_on_error=False):
            print(f"  {SCRIPT_PREFIX}ADVERTENCIA: 'git push -u origin main' falló.")
            print(f"                   Esto puede ocurrir si el repositorio remoto tiene commits que no tienes localmente.")
            print(f"                   Considera 'git pull origin main --rebase' y luego reintenta el push, o si estás seguro")
            print(f"                   de que quieres sobreescribir el remoto (setup inicial), puedes probar 'git push -u origin main --force'.")
            # No retornamos False aquí necesariamente, el repo y remoto están configurados.
            # El usuario puede necesitar intervenir manualmente.
        else:
            print(f"  {SCRIPT_PREFIX}[OK] Push a origin/main exitoso (o la rama ya estaba actualizada).")
    else:
        print(f"{SCRIPT_PREFIX}[INFO] No hay commits locales para hacer push (o el commit inicial falló).")


    print(f"\n{SCRIPT_PREFIX}--- Configuración de Repositorio GitHub Finalizada ---")
    print(f"{SCRIPT_PREFIX}Puedes acceder a tu repositorio en: https://github.com/{full_repo_name_gh}")
    print(f"\n{SCRIPT_PREFIX}[INFO]: NEXT STEP: El script orquestador continuará con los siguientes pasos de configuración.")
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
# tools/scripts/f00_files_setup/s03_setup_github_repo.py

## 🎯 Propósito

Inicializar el repositorio Git local, configurar un archivo `.gitignore` adecuado, y crear o conectar
con un repositorio remoto en GitHub. Este script automatiza los pasos comunes para poner un proyecto
bajo control de versiones con Git y sincronizarlo con GitHub.

---

## ⚙️ Funcionamiento Principal

El script sigue una serie de pasos para configurar el repositorio:

1.  **Verificación de GitHub CLI (`gh`)**:
    *   Comprueba si la CLI de GitHub (`gh`) está instalada y si el usuario está autenticado (`gh auth status`).
    *   Si `gh` no está instalada o el usuario no está autenticado, el script muestra un error y termina, ya que es necesaria para interactuar con GitHub.

2.  **Inicialización del Repositorio Git Local**:
    *   Verifica si ya existe un directorio `.git` en la raíz del proyecto.
    *   Si no existe, ejecuta `git init` para inicializar un nuevo repositorio Git.
    *   Establece la rama principal a `main` usando `git branch -M main`.
    *   Si el repositorio ya existe, simplemente asegura que la rama principal sea `main`.

3.  **Configuración de `.gitignore`**:
    *   Define una lista de reglas comunes para archivos y directorios que típicamente se ignoran en proyectos Python y Terraform (ej. `.env`, `.venv/`, `__pycache__/`, `terraform.tfstate*`).
    *   La función `ensure_gitignore_rules` lee el `.gitignore` existente (si lo hay) o crea uno nuevo.
    *   Añade cualquier regla de la lista que no esté ya presente en el archivo.
    *   Si no se puede actualizar `.gitignore`, el script termina para evitar commits de archivos sensibles.

4.  **Obtención de Información del Repositorio GitHub**:
    *   Intenta cargar variables de entorno `GITHUB_REPO_OWNER` y `GITHUB_REPO_NAME` desde un archivo `.env` (ubicado en `service/.env` o en la raíz del proyecto) si `python-dotenv` está instalado.
    *   Si estas variables no se encuentran, solicita al usuario:
        *   El nombre del repositorio (o `OWNER/NOMBRE_REPO`).
        *   El propietario del repositorio (usuario u organización de GitHub), intentando autodetectar el usuario autenticado con `gh api user -q .login` como sugerencia.
    *   Construye el nombre completo del repositorio en formato `OWNER/NOMBRE_REPO`.

5.  **Creación de Commit Inicial**:
    *   Verifica si ya existen commits en el repositorio local (`git rev-parse --verify HEAD`).
    *   Si no hay commits:
        *   Ejecuta `git add .` para añadir todos los archivos (respetando `.gitignore`).
        *   Crea un commit inicial con el mensaje "Fase 0: Estructura inicial y scripts de setup base".
        *   Si el commit falla (ej. no hay nada que commitear), lo informa.

6.  **Verificación/Creación de Repositorio Remoto en GitHub**:
    *   Utiliza `gh repo view OWNER/NOMBRE_REPO` para verificar si el repositorio ya existe en GitHub.
    *   Si no existe:
        *   Solicita al usuario una descripción para el repositorio y la visibilidad (public/private/internal).
        *   Ejecuta `gh repo create OWNER/NOMBRE_REPO --visibility --description --source=. --remote=origin` para crear el repositorio en GitHub, usando el directorio actual como fuente y configurando automáticamente el remote `origin`.
    *   Si el repositorio ya existe:
        *   Verifica si el remote `origin` está configurado localmente y si apunta a la URL HTTPS correcta (`https://github.com/OWNER/NOMBRE_REPO.git`).
        *   Si el remote `origin` es incorrecto, lo actualiza con `git remote set-url origin URL_CORRECTA`.
        *   Si el remote `origin` no existe, lo añade con `git remote add origin URL_CORRECTA`.

7.  **Push Inicial a GitHub**:
    *   Si hay commits locales:
        *   Intenta hacer push de la rama `main` al remote `origin` con `git push -u origin main`.
        *   Si el push falla, informa al usuario sobre posibles causas (conflictos con el remoto) y sugiere comandos para resolverlo (ej. `git pull`, `git push --force`). No termina el script por esto, ya que la configuración del repo puede estar bien.

8.  **Mensaje de Finalización**:
    *   Muestra la URL del repositorio en GitHub.
    *   Informa que la configuración ha terminado y que el script orquestador continuará.

La función `main()` devuelve `True` si los pasos críticos se completan exitosamente, `False` si hay un error que impide continuar (ej. `gh` no autenticado, fallo al actualizar `.gitignore`).

---

## ▶️ Uso

Este script está diseñado principalmente para ser llamado por el script orquestador `s00_main_initial_setup.py` después de la creación de la estructura y el venv.
También puede ser ejecutado directamente, pero asume que `git` y `gh` CLI están instalados y que el script se ejecuta desde una ubicación donde `utils_general.get_project_root()` pueda determinar correctamente la raíz del proyecto.

**Prerrequisitos**:
*   Git instalado y accesible en el PATH.
*   GitHub CLI (`gh`) instalada y accesible en el PATH.
*   El usuario debe haberse autenticado con GitHub CLI (`gh auth login`) previamente.

**Ejecución directa**:
Desde la raíz del proyecto (`PROJECT_ROOT`):
```bash
python tools/scripts/f00_files_setup/s03_setup_github_repo.py
```
o
```bash
python -m tools.scripts.f00_files_setup.s03_setup_github_repo
```

---

## 🧩 Dependencias

*   **Módulos del proyecto `tools.scripts`**:
    *   `utils_general` (alias `ug`): Para obtener la ruta raíz del proyecto y ejecutar comandos.
*   **Módulos estándar de Python**:
    *   `os`: Para variables de entorno y `os.name`.
    *   `subprocess`: Para ejecutar comandos de Git y `gh` directamente en algunos casos.
    *   `sys`: Para `sys.exit()`.
    *   `shutil`: Para `shutil.which()` para encontrar ejecutables.
    *   `pathlib`: Para manipulación de rutas.
*   **Paquetes externos (opcional, para `.env`)**:
    *   `python-dotenv`: Si está presente, se usa para cargar `GITHUB_REPO_OWNER` y `GITHUB_REPO_NAME` desde un archivo `.env`.

---

## 📄 Variables de Entorno Clave

El script puede utilizar las siguientes variables de entorno (cargadas desde `.env` si `python-dotenv` está disponible y el archivo existe):

*   `GITHUB_REPO_OWNER`: El propietario (usuario u organización) del repositorio en GitHub.
*   `GITHUB_REPO_NAME`: El nombre del repositorio en GitHub.

Si no se proporcionan, el script solicitará esta información al usuario.

---

## 📥 Entradas

*   **Variables de Entorno** (opcional, ver sección anterior).
*   **Input del Usuario**:
    *   Nombre del repositorio y/o propietario si no se definen por variables de entorno.
    *   Descripción del repositorio (opcional) si se crea uno nuevo.
    *   Visibilidad del repositorio (public/private/internal) si se crea uno nuevo.
*   **Estado del Sistema de Archivos**: Existencia de un directorio `.git`, contenido del `.gitignore`.
*   **Estado de Autenticación de `gh` CLI**.

---

## 📤 Salidas y Efectos Secundarios

*   **Sistema de Archivos**:
    *   Crea/modifica el directorio `.git` en la raíz del proyecto.
    *   Crea/modifica el archivo `.gitignore` en la raíz del proyecto.
*   **Repositorio Git Local**:
    *   Inicializa el repositorio si no existe.
    *   Establece la rama principal a `main`.
    *   Crea un commit inicial si no existen commits previos.
    *   Configura el remote `origin` para apuntar al repositorio de GitHub.
*   **Repositorio GitHub Remoto**:
    *   Puede crear un nuevo repositorio en GitHub si no existe.
*   **Sincronización**:
    *   Intenta hacer `git push` de la rama `main` al remote `origin`.
*   **Mensajes en Consola**: Imprime logs detallados del progreso, solicitudes de input, errores y mensajes de éxito.
*   **Código de Salida**: El script termina con `sys.exit(1)` si falla un paso crítico.

---

## ✅ Buenas Prácticas y Consideraciones

*   **Autenticación Previa de `gh`**: Es crucial que el usuario haya ejecutado `gh auth login` antes de correr este script para una experiencia fluida.
*   **Manejo de `.gitignore`**: Añadir reglas exhaustivas al `.gitignore` desde el inicio es una buena práctica para evitar commitear archivos no deseados o sensibles.
*   **Idempotencia Parcial**: El script intenta ser idempotente en la medida de lo posible (ej. no falla si Git ya está inicializado, si el `.gitignore` ya tiene las reglas, o si el repo remoto ya existe).
*   **Interacción con el Usuario**: Proporciona defaults razonables y solicita input cuando es necesario, guiando al usuario.
*   **Manejo de Errores y Sugerencias**: Intenta detectar errores comunes (ej. fallo de push) y ofrece sugerencias al usuario.
*   **Seguridad**: Al interactuar con GitHub, depende de la seguridad de la autenticación de `gh` CLI. No maneja credenciales directamente.
---
'''