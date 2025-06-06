
---

# Guía Definitiva de Configuración e Implementación: Data Ingestion PT MS (v6)

**Bienvenido/a al Proyecto de Ingesta de Datos!**

Esta guía te llevará paso a paso a través de la configuración completa de tu entorno de desarrollo y el despliegue del microservicio `DataIngestion_PT_MS`. El objetivo es tener un sistema robusto que obtiene datos de Alpaca Markets, los almacena en Google Cloud Firestore, notifica vía Pub/Sub, y se despliega en Google Cloud Run, todo gestionado con Terraform y automatizado con GitHub Actions.

**Dirigido a:** Desarrolladores, especialmente aquellos que están familiarizándose con GCP, Terraform, y flujos de CI/CD.

---

## Estructura del Proyecto

El proyecto está organizado en una estructura modular y clara que separa las responsabilidades:

```
DataIngestion_PT_MS/
├── service/                     # Todo lo relacionado con el microservicio
│   ├── app/                     # Código principal del microservicio
│   │   ├── __init__.py
│   │   ├── main.py              # Punto de entrada FastAPI
│   │   ├── alpaca_service.py    # Lógica de Alpaca
│   │   ├── config.py            # Configuración del servicio
│   │   └── gcp_clients.py       # Clientes de GCP
│   ├── tests/                   # Tests específicos del microservicio
│   │   ├── __init__.py
│   │   ├── test_alpaca_data.py
│   │   └── test_alpaca_fetch.py
│   ├── Dockerfile               # Docker para el servicio
│   └── requirements.txt         # Dependencias del servicio
│
├── tools/                       # Herramientas de desarrollo y despliegue
│   ├── scripts/                 # Scripts de gestión
│   │   ├── f00_files_setup/     # Scripts de configuración inicial
│   │   ├── f03_terraform_management/
│   │   ├── f04_gcp_setup/       # Configuración de GCP
│   │   ├── f05_data/            # Scripts de datos
│   │   └── f06_deployment/      # Scripts de despliegue
│   └── tests/                   # Tests de integración y cliente
│       ├── client_test.py
│       └── requirements-test.txt
│
├── terraform/                   # Configuración de infraestructura
│   ├── main.tf
│   └── variables.tf
│
└── docs/                        # Documentación del proyecto

### Organización del Proyecto

El proyecto está organizado de manera modular para separar claramente las responsabilidades:

#### Carpeta `service/`
Contiene todo lo relacionado con el microservicio en sí:
- `app/`: Código fuente del microservicio
  - `main.py`: Punto de entrada FastAPI y endpoints
  - `alpaca_service.py`: Lógica de negocio para Alpaca
  - `config.py`: Configuración y variables de entorno
  - `gcp_clients.py`: Clientes para servicios de GCP
- `tests/`: Tests unitarios y funcionales del servicio
- `Dockerfile`: Configuración para contenedorización
- `requirements.txt`: Dependencias del servicio

#### Carpeta `tools/`
Contiene herramientas de desarrollo, pruebas y despliegue:
- `scripts/`: Scripts de gestión y automatización
  - `f00_files_setup/`: Configuración inicial del proyecto
  - `f03_terraform_management/`: Gestión de Terraform
  - `f04_gcp_setup/`: Configuración de GCP
  - `f05_data/`: Scripts para manejo de datos
  - `f06_deployment/`: Scripts de despliegue
- `tests/`: Tests de integración y cliente de pruebas
  - `client_test.py`: Cliente WebSocket para pruebas
  - `requirements-test.txt`: Dependencias de pruebas

#### Carpeta `terraform/`
Contiene la configuración de infraestructura como código:
- `main.tf`: Configuración principal de recursos
- `variables.tf`: Definición de variables
- `outputs.tf`: Outputs de Terraform
- Otros archivos de estado y configuración

#### Carpeta `docs/`
Contiene toda la documentación del proyecto:
- Guías de configuración
- Documentación técnica
- Guías de usuario

Esta estructura modular facilita:
- Mantenimiento independiente del servicio
- Separación clara de herramientas de desarrollo
- Gestión eficiente de pruebas
- Despliegue simplificado

## Fase 0: Restauración de Archivos y Setup Local Inicial

**Objetivo de esta Fase:**
Preparar tu máquina local con todos los archivos del proyecto, crear un entorno virtual de Python aislado para las dependencias, e inicializar tu repositorio Git local y conectarlo con un repositorio remoto en GitHub.

**Prerrequisitos (¡Importante! Instala esto ANTES de empezar):**

1.  **Python:** Versión 3.8 o superior. Verifica con `python --version`.
2.  **Git:** Sistema de control de versiones. Verifica con `git --version`. [Descargar Git](https://git-scm.com/downloads)
3.  **GitHub CLI (`gh`):** Herramienta de línea de comandos para interactuar con GitHub. Verifica con `gh --version`. [Instalar GitHub CLI](https://cli.github.com/)
4.  **Google Cloud SDK (`gcloud` CLI):** Herramienta de línea de comandos para interactuar con Google Cloud Platform. Verifica con `gcloud version`. [Instalar Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
5.  **VS Code (Recomendado):** Un editor de código popular con excelente soporte para Python y terminal integrada. [Descargar VS Code](https://code.visualstudio.com/)
    *   **Extensión de Python para VS Code:** Búscala e instálala desde el panel de extensiones de VS Code (ej. la de Microsoft).
6.  **Carpeta de Restauración del Proyecto:** Debes tener una carpeta (ej. `_restore_DataIngestion_PT_MS/`) que contenga:
    *   `_restore_files.ps1`: El script PowerShell que hemos desarrollado para restaurar el proyecto.
    *   `project_map.json`: El archivo JSON que define la estructura de directorios y el mapeo de archivos para la restauración.
    *   `BckUp_Files/`: Una subcarpeta que contenga **todos los archivos fuente** del proyecto (scripts, archivos de configuración, etc.), nombrados exactamente como las **claves** definidas en la sección `file_mappings` de tu `project_map.json`.

**Pasos Detallados de la Fase 0:**

1.  **Paso 0.1: Ejecutar Script de Restauración de Archivos (PowerShell)**
    *   **Propósito:** Crear la estructura de directorios de tu proyecto y copiar todos los archivos base desde tu backup a tu directorio de trabajo.
    *   **Acción:**
        1.  Abre una terminal de **PowerShell**.
        2.  Navega (`cd`) a la carpeta que contiene tu directorio de restauración (donde está `_restore_DataIngestion_PT_MS/` y, dentro de él, `_restore_files.ps1`).
        3.  Si es la primera vez que ejecutas scripts de PowerShell descargados o no firmados en tu sistema o en esta sesión, puede que necesites ajustar la política de ejecución para permitirlo. Ejecuta:
            ```powershell
            Set-ExecutionPolicy Unrestricted -Scope Process
            ```
            Esto aplica la política solo para la sesión actual de PowerShell, por lo que es seguro.
        4.  Ejecuta el script de restauración. El script `_restore_files.ps1` tiene una variable `$dest_root_dir` codificada con una ruta de ejemplo. **Debes editar esa variable DENTRO del script `_restore_files.ps1` para que apunte al directorio donde quieres que se cree tu proyecto `DataIngestion_PT_MS`** (ej. `C:\MisProyectos\DataIngestion_PT_MS` o `G:\Mi unidad\...\DataIngestion_PT_MS`).
            ```powershell
            .\_restore_DataIngestion_PT_MS\_restore_files.ps1
            ```
    *   **Verificación:** Observa la salida del script. Debería indicar qué directorios se crearon y qué archivos se copiaron. Presta atención al resumen final, especialmente a "Files successfully copied" y "Files skipped (source not found)". Si hay muchos "source not found", significa que tu carpeta `BckUp_Files/` no está completa según `project_map.json`. Debes arreglar esto antes de continuar.
    *   **Acción Post-Restauración (¡CRUCIAL!):**
        1.  Navega a la carpeta de tu proyecto recién restaurada (`PROJECT_ROOT`, ej. `G:\Mi unidad\01_PROYECTOS\02_POS\DataIngestion_PT_MS`).
        2.  Abre el archivo `PROJECT_ROOT/service/.env`. Este archivo fue restaurado desde tu backup (probablemente desde un archivo llamado `_env` o `env_local_empty.env` en `BckUp_Files/`).
        3.  **Edita `.env` y completa TODAS las variables necesarias con tus valores reales o los valores iniciales para esta prueba.** Presta especial atención a:
            *   `GOOGLE_CLOUD_PROJECT_ID`: El ID del proyecto GCP que intentarás usar o crear (ej. `data-ingestion-pt-ms-v00X`).
            *   `GCP_BILLING_ACCOUNT_ID`: **Tu ID de cuenta de facturación real de GCP.** Sin esto, no podrás crear ni usar la mayoría de los servicios de GCP.
            *   `GCP_REGION`: ej. `us-central1`.
            *   `GITHUB_REPO_OWNER`: Tu nombre de usuario o el de tu organización en GitHub.
            *   `GITHUB_REPO_NAME`: El nombre que quieres para tu repositorio en GitHub (ej. `DataIngestion_PT_MS`).
            *   `WIF_POOL_BASE_NAME`: ej. `ghpool`.
            *   `WIF_POOL_START_SUFFIX`: ej. `1`.
            *   `WIF_PROVIDER_ID`: ej. `github-provider`.
            *   Credenciales de Alpaca (`ALPACA_API_KEY_ID`, `ALPACA_SECRET_KEY`): Pon placeholders si aún no quieres usar las reales, pero recuerda que la aplicación las necesitará.
            *   Revisa todas las demás variables y ajústalas según sea necesario.
        4.  Abre `PROJECT_ROOT/requirements.txt`. Este archivo también fue restaurado. Asegúrate de que contenga todas las dependencias Python que necesitará el proyecto (FastAPI, Uvicorn, Pydantic, google-cloud-*, python-dotenv, etc.).

2.  **Paso 0.2: Ejecutar Script de Setup Inicial Python (Estructura, Venv, Git/GitHub)**
    *   **Propósito:** Verificar la estructura de archivos, crear un entorno virtual de Python aislado, e inicializar Git y el repositorio de GitHub.
    *   **Acción:**
        1.  Abre una nueva terminal (o usa la misma si lo prefieres, pero asegúrate de que no esté activo ningún otro entorno virtual de Python de otro proyecto).
        2.  **Navega al directorio raíz de tu proyecto (`PROJECT_ROOT`).**
            ```powershell
            cd "RUTA_A_TU_PROJECT_ROOT\DataIngestion_PT_MS"
            ```
        3.  Ejecuta el script orquestador `s00_main_initial_setup.py` como un módulo Python:
            ```bash
            python -m tools.scripts.f00_files_setup.s00_main_initial_setup 
            ```
            Los scripts están organizados en la carpeta `tools/scripts/` con prefijos `fXX_` para una mejor organización:
    *   **Interacción y Acciones del Script:**
        1.  **Estructura de Archivos (`s01_create_structure.py`):** El script verificará la estructura. Como ya ejecutaste `_restore_files.ps1`, la mayoría de los archivos y directorios ya deberían existir, y verás muchos mensajes `[SKIP]`. Si algo faltara, lo crearía como placeholder. Te pedirá confirmación para crear la "Etapa 2" de placeholders detallados; puedes elegir 's' (sí) o 'n' (no).
        2.  **Entorno Virtual (`s02_create_venv.py`):** Creará (o verificará si ya existe) un entorno virtual llamado `.venv/` dentro de `PROJECT_ROOT`.
        3.  **ACTIVAR VENV (Manual - ¡CRUCIAL!):** El script `s00_` hará una pausa y te mostrará el siguiente mensaje:
            ```
            SCRIPT s00_main_setup: GUÍA PARA EL USUARIO:
            *********************************************************************************
            ** POR FAVOR, ACTIVA EL ENTORNO VIRTUAL '.venv/' EN ESTA TERMINAL               **
            ** (O ABRE UNA NUEVA TERMINAL, NAVEGA A LA RAÍZ DEL PROYECTO Y ACTÍVALO AHÍ)    **
            ** ANTES DE CONTINUAR CON EL SIGUIENTE PASO.                                   **
            ... (comandos específicos para tu OS) ...
            *********************************************************************************
            Presiona Enter DESPUÉS de haber activado el entorno virtual para continuar...
            ```
            **Debes activar el entorno virtual en tu terminal.** Por ejemplo, en PowerShell:
            ```powershell
            .\.venv\Scripts\Activate.ps1
            ```
            Tu prompt de terminal debería cambiar para indicar que el venv está activo (ej. `(.venv) PS C:\...>`). Solo después de esto, presiona Enter en el script Python para que continúe.
        4.  **Configuración de Git y GitHub (`s03_setup_github_repo.py`):**
            *   **Autenticación `gh`:** El script verificará si estás autenticado con la CLI de GitHub. Si no lo estás, te dirá: `Por favor, ejecuta 'gh auth login' manualmente...`. Deberás abrir OTRA terminal (o pausar el script si es posible, aunque es más fácil otra terminal), ejecutar `gh auth login`, completar el proceso en el navegador, y luego volver al script (si el script `s03` se diseñó para reintentar o si `s00` lo re-ejecuta; por ahora, asume que debes autenticarte antes de que `s03` tenga éxito). Para este flujo, es mejor que ya hayas hecho `gh auth login` antes de este paso si es la primera vez.
            *   **Información del Repositorio:** El script te pedirá el `OWNER` de GitHub (tu usuario/organización) y el `REPO_NAME` (ej. `DataIngestion_PT_MS`). Puede que sugiera defaults basados en tu configuración de `gh` o el nombre de la carpeta del proyecto. Asegúrate de que estos coincidan con los valores que pusiste en `.env` para `GITHUB_REPO_OWNER` y `GITHUB_REPO_NAME`.
            *   **Acciones de Git/GitHub:** El script:
                *   Inicializará `git` en `PROJECT_ROOT` (si no lo está ya) con `git init`.
                *   Asegurará que la rama principal sea `main` with `git branch -M main`.
                *   Creará un commit inicial ("Fase 0: Estructura inicial...") si no existen commits.
                *   Intentará crear el repositorio remoto en GitHub.com usando `gh repo create ...`.
                *   Configurará el `remote origin` de tu repositorio local.
                *   Hará `git push -u origin main` para subir tus archivos iniciales.
    *   **Verificación:** Al final, revisa la salida del script. Debería indicar que la configuración de GitHub fue exitosa y darte la URL de tu repositorio en GitHub. Ve a esa URL en tu navegador para confirmar que el repositorio se creó y que los archivos iniciales están allí.

**Resultado de Fase 0:**
Tu proyecto local está completamente configurado: estructura de archivos creada/restaurada, entorno virtual Python `.venv/` creado (pero aún sin las dependencias específicas del proyecto instaladas), repositorio Git local inicializado y sincronizado con un repositorio remoto en GitHub. Tu archivo `.env` está poblado con tus configuraciones iniciales.

---

## Fase 1: Configuración del Proyecto GCP y Dependencias Python

**Objetivo:**
Asegurar que tengas un proyecto Google Cloud Platform (GCP) activo y con facturación habilitada, que tu `gcloud` CLI local esté configurada para usar este proyecto, y que todas las dependencias Python necesarias para el proyecto estén instaladas en tu entorno virtual.

**Prerrequisitos:**
*   Fase 0 completada.
*   Tu archivo `PROJECT_ROOT/.env` debe tener `GOOGLE_CLOUD_PROJECT_ID` (el ID del proyecto que quieres usar/crear) y `GCP_BILLING_ACCOUNT_ID` (tu ID de cuenta de facturación real y válida) correctamente definidos.

**Pasos:**

1.  **Paso 1.1: Autenticar con Google Cloud SDK (Manual)**
    *   **Propósito:** Dar permiso a la herramienta `gcloud` CLI (y a las Application Default Credentials - ADC) para actuar en tu nombre en GCP.
    *   **Acción (en tu terminal, el venv puede o no estar activo, no afecta a `gcloud` directamente):**
        1.  Autenticación de Usuario para `gcloud` CLI:
            ```bash
            gcloud auth login
            ```
            Sigue las instrucciones: se abrirá un navegador para que inicies sesión con tu cuenta de Google. Elige la cuenta que tiene los permisos necesarios para crear proyectos y gestionar la facturación.
        2.  Configurar Credenciales Predeterminadas de Aplicación (ADC):
            ```bash
            gcloud auth application-default login
            ```
            Esto también abrirá un navegador. Estas credenciales son las que usarán tus scripts Python (y otras librerías de Google) para autenticarse cuando se ejecuten localmente.
    *   **Verificación:** Después de cada comando, deberías ver un mensaje de éxito.

2.  **Paso 1.2: Ejecutar Script de Gestión del Entorno GCP**
    *   **Propósito:** Este script verificará tu autenticación `gcloud`, leerá el ID del proyecto y el ID de la cuenta de facturación de tu archivo `.env`, e intentará crear el proyecto en GCP (si no existe) o verificar que exista y esté activo. También vinculará la facturación y configurará tu `gcloud` CLI local para usar este proyecto.
    *   **Acción:**
        1.  Asegúrate de que tu entorno virtual `.venv/` esté **activado** en tu terminal actual (ej. `.\.venv\Scripts\Activate.ps1`).
        2.  Desde `PROJECT_ROOT`, ejecuta:
            ```bash
            python -m tools.scripts.f02_manage_gcp_environment 
            ```
    *   **Interacción y Resultados Esperados:**
        *   El script verificará tu autenticación.
        *   Leerá `GOOGLE_CLOUD_PROJECT_ID` y `GCP_BILLING_ACCOUNT_ID` de `.env`.
        *   Verificará si la cuenta de facturación es válida y accesible. Si no, fallará y te dará instrucciones.
        *   Intentará `gcloud projects describe TU_PROJECT_ID`.
            *   Si el proyecto existe y está `ACTIVE`, continuará.
            *   Si el proyecto existe pero **NO está `ACTIVE`** (ej. `DELETE_REQUESTED`), el script **fallará**. **Acción del Usuario:** Deberás editar `GOOGLE_CLOUD_PROJECT_ID` en tu `.env` a un ID de proyecto nuevo o diferente (ej. `mi-proyecto-v2`) y volver a ejecutar este script (`python -m scripts.f02_manage_gcp_environment`).
            *   Si el proyecto **NO existe**, el script intentará crearlo con `gcloud projects create TU_PROJECT_ID ...`.
                *   Si la creación falla (ej. el ID ya está tomado globalmente, no tienes permisos `resourcemanager.projectCreator`, o el ID está en período de "soft-delete"), el script **fallará**. **Acción del Usuario:** Deberás editar `GOOGLE_CLOUD_PROJECT_ID` en tu `.env` a un nuevo ID y volver a ejecutar este script.
        *   Si el proyecto se crea exitosamente o ya existía y estaba activo, el script intentará vincular la cuenta de facturación (si aún no está vinculada). Si esto falla, te dará instrucciones.
        *   Finalmente, ejecutará `gcloud config set project <ID_DEL_PROYECTO_ACTIVO>` y `gcloud auth application-default set-quota-project <ID_DEL_PROYECTO_ACTIVO>`.
    *   **Acción del Usuario (CRUCIAL después de éxito):** El script te recordará al final. Asegúrate de que la variable `GOOGLE_CLOUD_PROJECT_ID` en tu archivo `.env` contenga el ID del proyecto que el script acaba de configurar y que está **ACTIVO y con facturación**. Este es el ID que usará Terraform.

3.  **Paso 1.3: Instalar Dependencias Python**
    *   **Propósito:** Instalar todas las librerías Python listadas en `requirements.txt` dentro de tu entorno virtual activado. Estas librerías son necesarias para tus scripts de Terraform, los scripts de configuración de GCP post-Terraform, y tu aplicación FastAPI.
    *   **Acción:**
        1.  Asegúrate de que tu entorno virtual `.venv/` esté **activado**.
        2.  Asegúrate de que `PROJECT_ROOT/requirements.txt` esté completo con todas las dependencias.
        3.  Desde `PROJECT_ROOT`, ejecuta:
            ```bash
            pip install -r requirements.txt
            ```
    *   **Verificación:** El comando debería completarse sin errores. Puedes verificar con `pip list`.

**Resultado de Fase 1:**
Un proyecto GCP específico está creado (o verificado como activo), con facturación habilitada. Tu `gcloud` CLI local está configurada para apuntar a este proyecto, y el "quota project" de tus ADC también está alineado. Tu archivo `.env` tiene la variable `GOOGLE_CLOUD_PROJECT_ID` actualizada al ID de este proyecto activo. Tu entorno virtual Python (`.venv/`) ahora tiene todas las dependencias necesarias instaladas.

---

## Fase 2: Infraestructura como Código con Terraform

**Objetivo:** Crear la infraestructura de GCP (Artifact Registry, Pub/Sub, Firestore, SA, contenedores de Secretos, WIF Pool y Provider) usando Terraform.

**Prerrequisitos:**
*   Fase 1 completada.
*   Terraform CLI instalada.
*   Archivo `.env` con todas las variables necesarias para Terraform.
*   Entorno virtual activado con dependencias (especialmente `python-dotenv`).

**Pasos:**

1.  ✅ **Ejecutar `terraform init` y `validate` (Script):**
    *   Desde `PROJECT_ROOT` (venv activado):
        ```bash
        python -m scripts.f03_terraform_management.tf_init_validate
        ```

2.  ✅ **Ejecutar `terraform plan` (Script):**
    *   Desde `PROJECT_ROOT` (venv activado):
        ```bash
        python -m scripts.f03_terraform_management.tf_plan
        ```
    *   Esto determina `WORKLOAD_IDENTITY_POOL_ID_FINAL` y lo guarda en `.env`.
    *   Revisa el plan (`tfplan.out`).

3.  ✅ **Ejecutar `terraform apply` (Script):**
    *   Desde `PROJECT_ROOT` (venv activado):
        ```bash
        python -m scripts.f03_terraform_management.tf_apply
        ```
    *   Confirma con `yes`.

**Resultado de Fase 2:** Infraestructura de GCP creada y gestionada por Terraform. El archivo `.env` contiene `WORKLOAD_IDENTITY_POOL_ID_FINAL`.

---

## Fase 3: Configuración Específica de GCP Post-Terraform y Datos

**Objetivo:** Configurar permisos detallados para la Service Account, añadir versiones a los secretos de Alpaca en Secret Manager, configurar el binding de Workload Identity Federation para GitHub Actions, y poblar Firestore con datos iniciales.

**Prerrequisitos:**
*   Fase 2 completada.
*   Archivo `PROJECT_ROOT/.env` con `ALPACA_API_KEY_ID` y `ALPACA_SECRET_KEY` definidos con valores reales, y `WORKLOAD_IDENTITY_POOL_ID_FINAL` presente.
*   Entorno virtual activado.

**Pasos:**

1.  ✅ **Ejecutar Orquestador de Configuración GCP Post-Terraform (Script):**
    *   Desde `PROJECT_ROOT` (venv activado):
        ```bash
        python -m tools.scripts.f04_gcp_setup.s00_main_gcp_config 
        ```
        *(Este script llama a `s01_configure_sa_permissions.py`, `s02_manage_secrets.py`, `s03_configure_workload_identity.py` y `scripts.data.seed_firestore.py`)*.
    *   **Presta atención a la salida del script `s03_configure_workload_identity.py` para obtener los valores de `GCP_WORKLOAD_IDENTITY_PROVIDER` y `GCP_SERVICE_ACCOUNT_EMAIL`.**

2.  ✅ **Configurar Secretos en GitHub Repository:**
    *   Ve a tu repositorio en GitHub: `Settings` > `Secrets and variables` > `Actions`.
    *   Crea los "Repository secrets":
        *   `GCP_PROJECT_ID` (el ID del proyecto activo de tu `.env`).
        *   `GCP_WORKLOAD_IDENTITY_PROVIDER` (obtenido del script anterior).
        *   `GCP_SERVICE_ACCOUNT_EMAIL` (obtenido del script anterior).

**Resultado de Fase 3:** GCP completamente configurado, secretos de aplicación seguros, WIF listo para CI/CD, y Firestore con datos.

---

## Fase 4: Desarrollo de la Aplicación y CI/CD

**Objetivo:** Desarrollar la lógica de la aplicación FastAPI y configurar el pipeline de CI/CD para despliegues automáticos.

**Prerrequisitos:**
*   Fase 3 completada.
*   Entorno virtual activado con todas las dependencias.

**Pasos:**

1.  **Desarrollar Código de la Aplicación:**
    *   Completa el código en `PROJECT_ROOT/app/` (`main.py`, `alpaca_service.py`, `config.py`, `gcp_clients.py`).
    *   Asegúrate que `app/config.py` lea correctamente las variables de entorno.

2.  **Escribir/Completar `Dockerfile`:**
    *   Define cómo se construye tu imagen de contenedor.

3.  **Configurar Workflow de GitHub Actions:**
    *   Completa `PROJECT_ROOT/.github/workflows/ci_cd.yml`.
    *   El workflow usará los secretos de GitHub para autenticarse en GCP, construir, subir la imagen a Artifact Registry y desplegar en Cloud Run.

4.  **Pruebas y Despliegue:**
    *   Prueba tu aplicación localmente (ej. `uvicorn app.main:app --reload`).
    *   Haz `git push` a tu rama principal para disparar el workflow de CI/CD.
    *   Monitorea el pipeline y prueba el servicio desplegado en Cloud Run.

**Resultado de Fase 4:** Una aplicación funcional desplegada en Cloud Run, con un pipeline de CI/CD.

---

## Fase 5: Despliegue y Pruebas

### Despliegue Manual del Microservicio

Para desplegar manualmente el microservicio (sin usar CI/CD), puedes usar los scripts en `tools/scripts/f06_deployment/`:

1. **Usando Python:**
   ```bash
   python -m tools.scripts.f06_deployment.deploy_cloud_run
   ```
   O usando PowerShell:
   ```powershell
   .\tools\scripts\f06_deployment\deploy_cloud_run.ps1 -ProjectId $env:PROJECT_ID
   ```

### Pruebas del Microservicio

El proyecto incluye varios tipos de pruebas ubicadas en diferentes carpetas según su propósito:

#### Tests Unitarios y Funcionales
Ubicados en `service/tests/`:
```bash
# Ejecutar test de fetch de Alpaca
python -m service.tests.test_alpaca_fetch

# Ejecutar test de datos de Alpaca
python -m service.tests.test_alpaca_data
```

#### Tests de Integración y Cliente
Ubicados en `tools/tests/`:

1. **Cliente WebSocket Interactivo:**
   ```bash
   python -m tools.tests.client_test
   ```
   Este cliente permite:
   - Suscribirse a símbolos específicos
   - Ver actualizaciones en tiempo real
   - Alternar entre vista detallada y resumida

2. **Scripts de Prueba Específicos:**
   ```powershell
   # Ejecutar cliente de prueba
   .\tools\tests\run_client.ps1
   
   # Ejecutar prueba de fetch
   .\tools\tests\run_fetch_test.ps1
   ```

### Monitoreo y Logs

Los logs del servicio se pueden encontrar en:
- Logs de desarrollo: `logs/`
- Logs en producción: Google Cloud Logging

Para ver los logs en Cloud Run:
```bash
gcloud logs tail --project=$env:PROJECT_ID "resource.type=cloud_run_revision"
```

### Estructura de Archivos de Prueba

```
service/tests/          # Tests del microservicio
├── __init__.py
├── test_alpaca_data.py  # Tests de la lógica de datos
└── test_alpaca_fetch.py # Tests de fetch de Alpaca

tools/tests/            # Tests de integración y cliente
├── __init__.py
├── client_test.py      # Cliente WebSocket interactivo
├── read_firestore_bars.py
└── requirements-test.txt
```

### Recomendaciones para las Pruebas

1. **Tests Unitarios:**
   - Ejecutar los tests en `service/tests/` durante el desarrollo
   - Asegurarse de que todos los tests pasen antes de hacer commit

2. **Tests de Integración:**
   - Usar el cliente WebSocket para probar el servicio desplegado
   - Verificar la correcta transmisión de datos
   - Probar diferentes patrones de suscripción

3. **Monitoreo:**
   - Revisar los logs regularmente
   - Configurar alertas en Cloud Monitoring
   - Verificar las métricas de Cloud Run

4. **CI/CD:**
   - Los tests unitarios se ejecutan automáticamente en el pipeline
   - Verificar los resultados en GitHub Actions
   - Monitorear los despliegues automáticos

## Recomendaciones y Mejores Prácticas

### Organización del Código

1. **Estructura Modular:**
   - Mantener el código del servicio en `service/app/`
   - Mantener las herramientas de desarrollo en `tools/`
   - Separar claramente las pruebas según su propósito

2. **Gestión de Dependencias:**
   - Mantener `service/requirements.txt` solo con dependencias del servicio
   - Usar `tools/tests/requirements-test.txt` para dependencias de pruebas
   - Documentar las versiones exactas de las dependencias

3. **Scripts de Automatización:**
   - Organizar los scripts por funcionalidad en `tools/scripts/`
   - Usar los prefijos `fXX_` para indicar el orden de ejecución
   - Mantener utils comunes en módulos compartidos

### Desarrollo

1. **Entorno Virtual:**
   - Siempre usar el entorno virtual para desarrollo
   - Mantener las dependencias actualizadas
   - Documentar cualquier nueva dependencia

2. **Tests:**
   - Escribir tests unitarios para nueva funcionalidad
   - Mantener los tests de integración actualizados
   - Usar el cliente de pruebas para verificar cambios

3. **Documentación:**
   - Mantener la documentación actualizada
   - Documentar nuevos endpoints o cambios en la API
   - Actualizar las guías de configuración según sea necesario

### Despliegue

1. **CI/CD:**
   - Revisar los workflows de GitHub Actions
   - Mantener los secretos actualizados
   - Verificar los despliegues automáticos

2. **Monitoreo:**
   - Configurar alertas apropiadas
   - Revisar logs regularmente
   - Mantener métricas relevantes

### Seguridad

1. **Secretos:**
   - Nunca commitear secretos al repositorio
   - Usar Secret Manager para credenciales
   - Mantener las claves de API seguras

2. **Permisos:**
   - Seguir el principio de mínimo privilegio
   - Revisar permisos regularmente
   - Documentar cambios en IAM

### Mantenimiento

1. **Updates:**
   - Mantener las dependencias actualizadas
   - Revisar advertencias de seguridad
   - Actualizar versiones de runtime según sea necesario

2. **Limpieza:**
   - Eliminar código no utilizado
   - Mantener los logs rotados
   - Limpiar recursos no utilizados en GCP

3. **Backup:**
   - Mantener copias de seguridad de datos críticos
   - Documentar procedimientos de recuperación
   - Verificar restauraciones periódicamente

## Mantenimiento de la Estructura del Proyecto

### Añadir Nuevas Funcionalidades

1. **Código del Servicio:**
   - Nuevos módulos van en `service/app/`
   - Tests relacionados van en `service/tests/`
   - Actualizar `service/requirements.txt` si es necesario

2. **Herramientas de Desarrollo:**
   - Nuevos scripts van en el directorio apropiado en `tools/scripts/`
   - Tests de herramientas van en `tools/tests/`
   - Mantener la numeración `fXX_` consistente

3. **Documentación:**
   - Actualizar este documento para reflejar cambios
   - Mantener README.md actualizado
   - Documentar nuevas herramientas

### Gestión de Dependencias

1. **Servicio Principal:**
   ```bash
   # Actualizar dependencias del servicio
   cd service
   pip install -r requirements.txt
   ```

2. **Herramientas de Desarrollo:**
   ```bash
   # Actualizar dependencias de pruebas
   cd tools/tests
   pip install -r requirements-test.txt
   ```

### Actualizando Scripts

1. **Scripts de Despliegue:**
   - Modificar `tools/scripts/f06_deployment/`
   - Probar cambios localmente antes de commit

2. **Scripts de Configuración:**
   - Actualizar scripts en `tools/scripts/f04_gcp_setup/`
   - Mantener utils comunes en módulos compartidos

3. **Scripts de Prueba:**
   - Modificar `tools/tests/`
   - Actualizar documentación de uso

### Gestión de Logs

1. **Logs de Desarrollo:**
   ```
   logs/
   ├── development.log
   └── test.log
   ```

2. **Logs de Producción:**
   - Configurados en Cloud Run
   - Accesibles vía Cloud Logging

### Control de Versiones

1. **Estructura de Branches:**
   ```
   main
   ├── feature/
   ├── bugfix/
   └── release/
   ```

2. **Commits:**
   - Usar mensajes descriptivos
   - Referenciar issues cuando aplique
   - Mantener commits atómicos

### Backups y Restauración

1. **Respaldos:**
   - Mantener `docs/_restore/` actualizado
   - Actualizar `project_map.json`
   - Documentar cambios en la estructura

2. **Restauración:**
   ```powershell
   # Desde el directorio _restore
   .\_restore_files.ps1
   ```

### Recomendaciones Adicionales

1. **Nuevos Desarrolladores:**
   - Empezar por esta documentación
   - Revisar la estructura del proyecto
   - Seguir las convenciones establecidas

2. **Cambios en la Estructura:**
   - Discutir cambios mayores en equipo
   - Documentar razones de cambios
   - Mantener la separación de responsabilidades

3. **Mantenimiento Regular:**
   - Revisar y actualizar dependencias
   - Limpiar archivos temporales
   - Mantener la documentación al día

