# PROJECT_ROOT/tools/scripts/f02_manage_gcp_environment.py
import os
import subprocess
import sys
import time
import json
from pathlib import Path
from dotenv import load_dotenv
import shutil

# MODIFICADO: Importación absoluta desde el paquete 'tools'
from tools.scripts import utils_general as ug

# Nombres de las variables de entorno esperadas en .env
ENV_VAR_PROJECT_ID = "GOOGLE_CLOUD_PROJECT_ID"
ENV_VAR_BILLING_ACCOUNT = "GCP_BILLING_ACCOUNT_ID"
ENV_VAR_ORGANIZATION_ID = "GCP_ORGANIZATION_ID" # Opcional
ENV_VAR_FOLDER_ID = "GCP_FOLDER_ID"             # Opcional

SCRIPT_PREFIX = "SCRIPT f02_manage_gcp_env: "

# --- FUNCIONES AUXILIARES DEFINIDAS PRIMERO ---

def check_gcloud_auth_status() -> tuple[bool, str | None]:
    """Verifica la autenticación de gcloud. Devuelve (True, active_account_email) o (False, None)."""
    print(f"{SCRIPT_PREFIX}Verificando autenticación de gcloud...")
    gcloud_exe = shutil.which("gcloud.cmd") if os.name == 'nt' else shutil.which("gcloud")
    if not gcloud_exe:
        print(f"  {SCRIPT_PREFIX}ERROR CRÍTICO: 'gcloud' CLI no encontrada. Instálala y configúrala en tu PATH.")
        return False, None

    active_account_email = None
    try:
        auth_list_cmd = [gcloud_exe, "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"]
        use_shell = (os.name == 'nt')
        auth_cmd_arg = subprocess.list2cmdline(auth_list_cmd) if use_shell else auth_list_cmd
        auth_proc = subprocess.run(auth_cmd_arg, capture_output=True, text=True, shell=use_shell, check=False, encoding="utf-8", errors="replace")

        if auth_proc.returncode == 0 and auth_proc.stdout.strip():
            active_account_email = auth_proc.stdout.strip()
            print(f"  {SCRIPT_PREFIX}[OK] Autenticado con cuenta activa: {active_account_email}")
        else:
            print(f"  {SCRIPT_PREFIX}ERROR: No hay cuenta activa en gcloud.")
            if auth_proc.stdout.strip(): print(f"                       (STDOUT: '{auth_proc.stdout.strip()}')")
            if auth_proc.stderr.strip(): print(f"                       (STDERR: '{auth_proc.stderr.strip()}')")
            print(f"                       GUÍA: Ejecuta 'gcloud auth login' manualmente.")
            return False, None

        adc_cmd = [gcloud_exe, "auth", "application-default", "print-access-token"]
        adc_proc = subprocess.run(subprocess.list2cmdline(adc_cmd) if use_shell else adc_cmd,
                                  capture_output=True, text=True, shell=use_shell, check=False, encoding="utf-8", errors="replace")
        if not (adc_proc.returncode == 0 and adc_proc.stdout.strip()):
            print(f"  {SCRIPT_PREFIX}ADVERTENCIA: Application Default Credentials (ADC) no configuradas o falló la obtención de token.")
            print(f"                       GUÍA: Ejecuta 'gcloud auth application-default login' si los scripts Python lo requieren para acceso local a GCP.")
        else:
            print(f"  {SCRIPT_PREFIX}[OK] Application Default Credentials (ADC) configuradas.")
        return True, active_account_email
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR inesperado verificando autenticación: {e}")
        return False, None

def verify_billing_account(billing_account_id: str, project_root_path: Path, active_gcloud_account: str | None) -> bool:
    """Verifica si la cuenta de facturación es accesible usando 'describe'."""
    if not billing_account_id:
        print(f"  {SCRIPT_PREFIX}ERROR (verify_billing): No se proporcionó ID de cuenta de facturación.")
        return False

    print(f"\n{SCRIPT_PREFIX}Verificando accesibilidad de la cuenta de facturación '{billing_account_id}'...")
    gcloud_exe = shutil.which("gcloud.cmd") if os.name == 'nt' else shutil.which("gcloud")
    if not gcloud_exe:
        print(f"  {SCRIPT_PREFIX}ERROR (verify_billing): 'gcloud' CLI no encontrada.")
        return False

    expected_output_name = f"billingAccounts/{billing_account_id}"
    check_billing_cmd = [
        gcloud_exe, "beta", "billing", "accounts", "describe", billing_account_id,
        "--format=value(name)"
    ]

    use_shell = (os.name == 'nt')
    cmd_arg = subprocess.list2cmdline(check_billing_cmd) if use_shell else check_billing_cmd
    print(f"  {SCRIPT_PREFIX}Ejecutando: gcloud beta billing accounts describe {billing_account_id} ...")
    try:
        proc = subprocess.run(cmd_arg, capture_output=True, text=True, shell=use_shell, check=False, encoding="utf-8", errors="replace")

        stdout_cleaned = proc.stdout.strip()
        if proc.returncode == 0 and stdout_cleaned.lower() == expected_output_name.lower():
            print(f"  {SCRIPT_PREFIX}[OK] Cuenta de facturación '{billing_account_id}' (Nombre completo: '{stdout_cleaned}') encontrada y accesible.")
            return True
        else:
            active_account_display = active_gcloud_account if active_gcloud_account else "la cuenta actualmente autenticada con gcloud"
            print(f"  {SCRIPT_PREFIX}ERROR: Cuenta de facturación '{billing_account_id}' no se pudo verificar (esperado '{expected_output_name.lower()}', obtenido '{stdout_cleaned.lower()}').")
            print(f"         Salida del comando (stdout): '{stdout_cleaned}'")
            if proc.stderr.strip(): print(f"         Salida del comando (stderr): '{proc.stderr.strip()}'")
            print(f"         Código de retorno del comando: {proc.returncode}")
            print(f"         GUÍA: Verifica el ID '{ENV_VAR_BILLING_ACCOUNT}' en tu 'service/.env'. Asegúrate de que {active_account_display}")
            print(f"               tenga al menos el rol 'Visualizador de cuentas de facturación' (roles/billing.viewer) sobre la cuenta de facturación '{billing_account_id}'.")
            return False
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ERROR inesperado verificando cuenta de facturación: {e}")
        return False

# --- FUNCIÓN PRINCIPAL DE LÓGICA ---

def manage_project_lifecycle(project_root: Path) -> str | None:
    """
    Maneja la creación/verificación del proyecto GCP, vinculación de facturación,
    y configuración de gcloud local. Devuelve el ID del proyecto activo o None.
    """
    auth_ok, active_user_account = check_gcloud_auth_status() # Ahora Pylance debería ver esta función
    if not auth_ok:
        return None

    env_path = project_root / "service" / ".env"
    if not env_path.exists():
        print(f"{SCRIPT_PREFIX}ERROR: Archivo 'service/.env' no encontrado en el proyecto.")
        return None
    load_dotenv(env_path)
    print(f"{SCRIPT_PREFIX}[INFO] Cargado 'service/.env' desde: {env_path}")

    project_id_from_env = os.getenv(ENV_VAR_PROJECT_ID)
    billing_account_id = os.getenv(ENV_VAR_BILLING_ACCOUNT)
    org_id = os.getenv(ENV_VAR_ORGANIZATION_ID)
    folder_id = os.getenv(ENV_VAR_FOLDER_ID)

    if not project_id_from_env:
        print(f"{SCRIPT_PREFIX}ERROR: Variable '{ENV_VAR_PROJECT_ID}' debe estar definida en 'service/.env'.")
        return None
    if not billing_account_id:
        print(f"{SCRIPT_PREFIX}ERROR: Variable '{ENV_VAR_BILLING_ACCOUNT}' debe estar definida en 'service/.env'.")
        return None

    if not verify_billing_account(billing_account_id, project_root, active_user_account): # Ahora Pylance debería ver esta función
        return None

    print(f"\n{SCRIPT_PREFIX}--- Trabajando con ID de Proyecto (de .env): '{project_id_from_env}' ---")
    gcloud_exe = shutil.which("gcloud.cmd") if os.name == 'nt' else shutil.which("gcloud")
    if not gcloud_exe:
        print(f"{SCRIPT_PREFIX}ERROR CRITICO: 'gcloud' CLI no encontrada. No se puede continuar.")
        return None

    project_is_active = False
    project_exists = False
    proc_describe = None # Inicializar a None

    print(f"{SCRIPT_PREFIX}Verificando estado del proyecto '{project_id_from_env}'...")
    try:
        describe_cmd_list = [gcloud_exe, "projects", "describe", project_id_from_env, "--format=json"]
        proc_describe = subprocess.run(
            subprocess.list2cmdline(describe_cmd_list) if os.name == 'nt' else describe_cmd_list,
            capture_output=True, text=True, check=False, shell=(os.name == 'nt'), encoding="utf-8", errors="replace"
        )
        if proc_describe.returncode == 0:
            project_data = json.loads(proc_describe.stdout)
            lifecycle_state = project_data.get("lifecycleState")
            print(f"  {SCRIPT_PREFIX}[INFO] Proyecto '{project_id_from_env}' ya existe. Estado: {lifecycle_state}")
            project_exists = True
            if lifecycle_state == "ACTIVE":
                project_is_active = True
            else:
                print(f"  {SCRIPT_PREFIX}ERROR FATAL: Proyecto '{project_id_from_env}' existe pero su estado es '{lifecycle_state}'.")
                print(f"                       GUÍA: Actualiza '{ENV_VAR_PROJECT_ID}' en tu 'service/.env' a un ID de proyecto nuevo/diferente y vuelve a ejecutar.")
                return None
        else:
            print(f"  {SCRIPT_PREFIX}[INFO] Proyecto '{project_id_from_env}' no encontrado (o error al describir).")
            if proc_describe.stderr.strip():
                 print(f"    Error de gcloud: {proc_describe.stderr.strip()}")
            print(f"  {SCRIPT_PREFIX}Se intentará crear.")

    except json.JSONDecodeError as e_json:
        print(f"  {SCRIPT_PREFIX}ERROR: Falló el parseo de JSON al describir proyecto '{project_id_from_env}': {e_json}")
        if proc_describe and proc_describe.stdout:
            print(f"    DEBUG: Describe stdout: {proc_describe.stdout.strip()}")
        else:
            print(f"    DEBUG: No hubo salida stdout de 'gcloud projects describe' o proc_describe no está definido.")
        return None
    except Exception as e:
        print(f"  {SCRIPT_PREFIX}ADVERTENCIA: Excepción al describir proyecto '{project_id_from_env}': {e}. Se intentará crear.")

    if not project_exists:
        print(f"\n{SCRIPT_PREFIX}Intentando crear proyecto GCP ID: '{project_id_from_env}'...")
        create_cmd = ["gcloud", "projects", "create", project_id_from_env, "--name", project_id_from_env]
        if org_id: create_cmd.extend(["--organization", org_id])
        elif folder_id: create_cmd.extend(["--folder", folder_id])

        if not ug.run_command_in_dir(create_cmd, str(project_root)):
            print(f"  {SCRIPT_PREFIX}ERROR FATAL: No se pudo crear el proyecto '{project_id_from_env}'.")
            print(f"                       GUÍA: Verifica permisos (ej. 'resourcemanager.projectCreator'), unicidad del ID, o si está en 'soft-delete'.")
            print(f"                             Actualiza '{ENV_VAR_PROJECT_ID}' en 'service/.env' y reintenta.")
            return None
        print(f"  {SCRIPT_PREFIX}[OK] Proyecto '{project_id_from_env}' creado. Esperando 30s para propagación...")
        time.sleep(30)
        project_is_active = True

        print(f"\n{SCRIPT_PREFIX}Intentando vincular proyecto '{project_id_from_env}' a cuenta de facturación '{billing_account_id}'...")
        link_billing_cmd = ["gcloud", "beta", "billing", "projects", "link", project_id_from_env, "--billing-account", billing_account_id]
        if not ug.run_command_in_dir(link_billing_cmd, str(project_root)):
            print(f"  {SCRIPT_PREFIX}ERROR FATAL: No se pudo vincular facturación al proyecto '{project_id_from_env}'.")
            return None
        print(f"  {SCRIPT_PREFIX}[OK] Proyecto vinculado a la cuenta de facturación.")

    elif project_is_active:
         print(f"{SCRIPT_PREFIX}[INFO] Proyecto '{project_id_from_env}' ya existía y estaba activo. Verificando facturación...")
         billing_info_cmd = [gcloud_exe, "beta", "billing", "projects", "describe", project_id_from_env, "--format=json"]
         proc_billing_info = subprocess.run(subprocess.list2cmdline(billing_info_cmd) if os.name == 'nt' else billing_info_cmd,
                                           capture_output=True, text=True, shell=(os.name == 'nt'), check=False, encoding="utf-8", errors="replace")
         if proc_billing_info.returncode == 0:
             try:
                billing_data = json.loads(proc_billing_info.stdout)
                if billing_data.get("billingEnabled"):
                    print(f"  {SCRIPT_PREFIX}[OK] Facturación ya está habilitada para el proyecto '{project_id_from_env}'.")
                else:
                    print(f"  {SCRIPT_PREFIX}ADVERTENCIA: Facturación NO habilitada para '{project_id_from_env}'. Intentando vincular...")
                    link_billing_cmd = ["gcloud", "beta", "billing", "projects", "link", project_id_from_env, "--billing-account", billing_account_id]
                    if not ug.run_command_in_dir(link_billing_cmd, str(project_root)):
                        print(f"  {SCRIPT_PREFIX}ERROR: No se pudo vincular facturación al proyecto existente '{project_id_from_env}'.")
                        return None
                    print(f"  {SCRIPT_PREFIX}[OK] Proyecto vinculado a la cuenta de facturación.")
             except json.JSONDecodeError:
                print(f"  {SCRIPT_PREFIX}ADVERTENCIA: No se pudo parsear la información de facturación para '{project_id_from_env}'. STDOUT: {proc_billing_info.stdout.strip()}")
         else:
            print(f"  {SCRIPT_PREFIX}ADVERTENCIA: No se pudo obtener información de facturación para el proyecto '{project_id_from_env}'.")
            if proc_billing_info.stderr.strip(): print(f"                   STDERR: {proc_billing_info.stderr.strip()}")

    if project_is_active:
        print(f"\n{SCRIPT_PREFIX}Estableciendo '{project_id_from_env}' como proyecto por defecto en gcloud CLI...")
        set_project_cmd = ["gcloud", "config", "set", "project", project_id_from_env]
        if not ug.run_command_in_dir(set_project_cmd, str(project_root), suppress_stdout_if_captured=True):
            print(f"  {SCRIPT_PREFIX}ERROR: No se pudo establecer '{project_id_from_env}' como proyecto por defecto en gcloud.")
            return None

        current_gcloud_project_config = ug.get_gcloud_project_config()
        if current_gcloud_project_config == project_id_from_env:
            print(f"  {SCRIPT_PREFIX}[OK] Proyecto por defecto de gcloud CLI configurado a: {current_gcloud_project_config}")

            print(f"\n{SCRIPT_PREFIX}Configurando '{project_id_from_env}' como Quota Project para Application Default Credentials...")
            set_quota_project_cmd = ["gcloud", "auth", "application-default", "set-quota-project", project_id_from_env]
            if not ug.run_command_in_dir(set_quota_project_cmd, str(project_root), exit_on_error=False, suppress_stdout_if_captured=True):
                print(f"  {SCRIPT_PREFIX}ADVERTENCIA: No se pudo establecer '{project_id_from_env}' como Quota Project para ADC.")
                print(f"               Podrías necesitar ejecutar 'gcloud auth application-default set-quota-project {project_id_from_env}' manualmente si encuentras errores de cuota con las ADC.")
            else:
                print(f"  {SCRIPT_PREFIX}[OK] Quota Project para ADC configurado a: {project_id_from_env}")

            print(f"\n{SCRIPT_PREFIX}--- Configuración del proyecto GCP '{project_id_from_env}' finalizada exitosamente. ---")
            print(f"{SCRIPT_PREFIX}GUÍA: La variable '{ENV_VAR_PROJECT_ID}' en tu archivo 'service/.env' está establecida a '{project_id_from_env}'.")
            print(f"      Esta es la que usarán los scripts de Terraform y otros scripts de GCP.")
            return project_id_from_env
        else:
            print(f"  {SCRIPT_PREFIX}ERROR: Se intentó configurar '{project_id_from_env}', pero gcloud CLI reporta '{current_gcloud_project_config}' como proyecto actual.")
            return None

    return None

# --- PUNTO DE ENTRADA PRINCIPAL DEL SCRIPT ---

def main():
    project_root = ug.get_project_root()
    print(f"{SCRIPT_PREFIX}--- Orquestador de Configuración de Proyecto GCP ---")
    print(f"{SCRIPT_PREFIX}Raíz del proyecto detectada: {project_root}")

    effective_project_id = manage_project_lifecycle(project_root)

    if not effective_project_id:
        print(f"\n{SCRIPT_PREFIX}El proceso de configuración del proyecto GCP no pudo completarse exitosamente.")
        print(f"{SCRIPT_PREFIX}Por favor, revisa los mensajes anteriores, ajusta tu archivo 'service/.env' o la configuración/permisos de GCP y reintenta.")
        sys.exit(1)
    else:
        print(f"\n{SCRIPT_PREFIX}¡Proceso de gestión del proyecto GCP '{effective_project_id}' finalizado exitosamente!")
        print(f"{SCRIPT_PREFIX}Asegúrate de que la variable '{ENV_VAR_PROJECT_ID}' en tu 'service/.env' esté establecida a: {effective_project_id}")

if __name__ == "__main__":
    current_script_path = Path(__file__).resolve()
    # tools/scripts/f02_manage_gcp_environment.py
    project_root_dir_for_import = current_script_path.parent.parent.parent # DataIngestion_PT_MS
    if str(project_root_dir_for_import) not in sys.path:
        sys.path.insert(0, str(project_root_dir_for_import))
    main()

'''
---

````markdown
# `f02_manage_gcp_environment.py`

## 🎯 Propósito

Gestiona el ciclo de vida de un proyecto en Google Cloud Platform (GCP), incluyendo:

- Verificación de autenticación con `gcloud`
- Comprobación y creación de proyectos en GCP
- Vinculación con cuenta de facturación GCP
- Configuración local de la CLI (Command Line interface) de `gcloud` y 
- Configuración de las ADC (Credenciales Predeterminadas de Aplicación) para la cuota de proyecto. 

---

## ⚙️ Funcionalidad Principal

### `check_gcloud_auth_status()`
- Verifica si la CLI de `gcloud` está instalada.
- Comprueba si hay una cuenta autenticada activa.
- Verifica si las ADC están configuradas (intentando obtener un token de acceso).

### `verify_billing_account()`
- Utiliza `gcloud beta billing accounts describe` para validar el acceso a la cuenta de facturación especificada.

### `manage_project_lifecycle()` *(Lógica Principal)*

1. Llama a `check_gcloud_auth_status()`.
2. Carga variables desde `service/.env`:
   - `GOOGLE_CLOUD_PROJECT_ID`
   - `GCP_BILLING_ACCOUNT_ID`
   - `GCP_ORGANIZATION_ID` *(opcional)*
   - `GCP_FOLDER_ID` *(opcional)*
3. Llama a `verify_billing_account()`.
4. **Verificación / Creación del Proyecto:**
   - Usa `gcloud projects describe` para revisar si el proyecto existe.
   - Si no existe, lo crea con `gcloud projects create` (opcionalmente asociado a una organización o carpeta).
5. **Vinculación de Facturación:**
   - Si el proyecto es nuevo o sin facturación activa, lo vincula usando `gcloud beta billing projects link`.
6. **Configuración Local de gcloud:**
   - Define el proyecto como predeterminado:
     ```bash
     gcloud config set project <ID>
     ```
   - Establece el proyecto de cuota para ADC:
     ```bash
     gcloud auth application-default set-quota-project <ID>
     ```

### `main()`
- Orquesta todo el proceso llamando a `manage_project_lifecycle()`.
- Sale con código `1` en caso de error.

---

## 📄 Variables de Entorno (`service/.env`)

| Variable                 | Descripción                                |
|--------------------------|--------------------------------------------|
| `GOOGLE_CLOUD_PROJECT_ID` | ID del proyecto en GCP                     |
| `GCP_BILLING_ACCOUNT_ID`  | ID de cuenta de facturación                |
| `GCP_ORGANIZATION_ID`     | (Opcional) ID de la organización           |
| `GCP_FOLDER_ID`           | (Opcional) ID de la carpeta dentro de GCP |

---

## 📦 Dependencias

- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- Librerías de Python:
  - `dotenv`
  - `shutil`
- Módulo interno:
  - `tools.scripts.utils_general`

---

## ▶️ Uso
Si se ejecuta directamente:
- Modifica `sys.path`
- Llama a `main()`

---

## 📥 Entradas
- Archivo `.env` con las variables necesarias
- Sesión autenticada previamente en la CLI de `gcloud`

---

## 📤 Salidas y Efectos Secundarios
- Posible creación de un nuevo proyecto GCP
- Vinculación con cuenta de facturación
- Modificación de configuración local de `gcloud` (proyecto predeterminado y de cuota ADC)
- Impresión de logs detallados y mensajes de estado

---

## ✅ Mejores Prácticas y Consideraciones
- **Permisos Requeridos:**
  - `resourcemanager.projectCreator`
  - `billing.user` o roles específicos para vincular facturación
  - Permisos de organización o carpeta, si aplica

- **Autenticación Previa:**
  - Ejecutar previamente:  
    ```bash
    gcloud auth login
    ```

- **Unicidad del Proyecto:**
  - El `GOOGLE_CLOUD_PROJECT_ID` debe ser globalmente único.

- **Impacto Potencial:**
  - Este script puede crear proyectos y vincular cuentas de facturación. Usar con precaución.

- **Idempotencia Parcial:**
  - No recrea proyectos existentes activos.
  - La configuración local de `gcloud` se actualiza en cada ejecución.

'''
