```markdown
# DataIngestion_PT_MS

Microservicio de ingesta de datos históricos de Alpaca Markets, diseñado para desplegarse en Google Cloud Run, utilizando Firestore para almacenamiento y Google Cloud Pub/Sub para la notificación de eventos. Este proyecto incluye scripts para la configuración automatizada del entorno, infraestructura como código con Terraform, y un pipeline de CI/CD con GitHub Actions.

## Tabla de Contenidos

- [Descripción](#descripción)
- [Arquitectura (General)](#arquitectura-general)
- [Prerrequisitos](#prerrequisitos)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Guía de Configuración e Implementación](#guía-de-configuración-e-implementación)
  - [Fase 0: Preparación del Entorno y Proyecto Local](#fase-0-preparación-del-entorno-y-proyecto-local)
  - [Fase 1: Infraestructura con Terraform e Instalación de Dependencias](#fase-1-infraestructura-con-terraform-e-instalación-de-dependencias)
  - [Fase 2: Configuración Específica de GCP y Datos](#fase-2-configuración-específica-de-gcp-y-datos)
  - [Fase 3: Desarrollo de la Aplicación y CI/CD](#fase-3-desarrollo-de-la-aplicación-y-cicd)
- [Variables de Entorno](#variables-de-entorno)
- [Scripts Principales](#scripts-principales)
- [Ejecución Local de la Aplicación](#ejecución-local-de-la-aplicación)
- [Despliegue](#despliegue)
- [Contribuciones](#contribuciones)
- [Licencia](#licencia)

## Descripción

Este microservicio se encarga de:
1.  Obtener periódicamente datos históricos (barras OHLCV) del mercado de acciones desde la API de Alpaca Markets.
2.  Procesar y almacenar estos datos en una base de datos Google Cloud Firestore.
3.  Publicar un evento en Google Cloud Pub/Sub cada vez que se actualizan los datos de un activo.
4.  Exponer un endpoint raíz para health checks y un endpoint WebSocket para la transmisión de los datos más recientes (estado del último fetch).

La aplicación está construida con FastAPI y programada para ejecutarse de forma continua utilizando APScheduler.

## Arquitectura (General)

- **Aplicación:** Python FastAPI.
- **Orquestación de Tareas:** APScheduler (dentro de la app FastAPI).
- **Fuente de Datos:** Alpaca Markets API.
- **Almacenamiento de Datos:** Google Cloud Firestore.
- **Mensajería de Eventos:** Google Cloud Pub/Sub.
- **Plataforma de Despliegue:** Google Cloud Run (serverless).
- **Registro de Contenedores:** Google Artifact Registry.
- **Infraestructura como Código (IaC):** Terraform.
- **CI/CD:** GitHub Actions con Workload Identity Federation para autenticación segura con GCP.

## Prerrequisitos

Antes de comenzar, asegúrate de tener instalado lo siguiente:

-   Python 3.8 o superior.
-   Git.
-   Google Cloud SDK (`gcloud` CLI).
-   GitHub CLI (`gh`).
-   Terraform CLI (versión >= 1.3).
-   Una cuenta de Google Cloud Platform con un proyecto creado (o estar listo para crear uno).
-   Una cuenta de GitHub.
-   Credenciales de API de Alpaca Markets (Key ID y Secret Key).

## Estructura del Proyecto

```
DataIngestion_PT_MS/
├── .devcontainer/         # Configuración para Dev Containers (opcional)
├── .github/
│   └── workflows/         # Workflows de GitHub Actions (ej. ci_cd.yml)
├── .vscode/               # Configuraciones específicas de VS Code
├── app/                   # Código fuente de la aplicación FastAPI
│   ├── __init__.py
│   ├── alpaca_service.py  # Lógica de interacción con Alpaca y Firestore/PubSub
│   ├── config.py          # Configuración de la aplicación (Pydantic)
│   ├── gcp_clients.py     # Inicialización de clientes GCP (Firestore, PubSub)
│   └── main.py            # Archivo principal de FastAPI, scheduler, endpoints
├── docs/                  # Documentación del proyecto
│   └── _restore/          # Scripts/archivos para restauración/referencia
├── logs/                  # (Opcional) Logs locales si se generan
├── scripts/               # Scripts de utilidad y automatización
│   ├── __init__.py
│   ├── config_gcp/        # Scripts para configurar GCP post-Terraform
│   ├── data/              # Scripts relacionados con datos (ej. seed_firestore.py)
│   ├── deployment/        # Scripts para despliegue (manual o componentes de CI/CD)
│   ├── setup/             # Scripts para la configuración inicial del proyecto
│   ├── terraform_management/ # Scripts para gestionar Terraform (init, plan, apply)
│   └── utils_general.py   # Funciones de utilidad comunes para los scripts
├── terraform/             # Archivos de configuración de Terraform (IaC)
├── tests/                 # Pruebas unitarias y de integración
├── .dockerignore          # Especifica qué archivos ignorar al construir la imagen Docker
├── .env                   # Variables de entorno locales (¡NO SUBIR A GIT!)
├── .env.example           # Ejemplo de archivo .env
├── .gitignore             # Especifica archivos y directorios a ignorar por Git
├── Dockerfile             # Define la imagen de contenedor para la aplicación
├── README.md              # Este archivo
└── requirements.txt       # Dependencias Python del proyecto
```

## Guía de Configuración e Implementación

Sigue la [Guia_Configuracion_Proyecto.md](./docs/Guia_Configuracion_Proyecto.md) para una configuración detallada paso a paso. A continuación, un resumen del flujo:

### Fase 0: Preparación del Entorno y Proyecto Local
1.  Crea la carpeta raíz del proyecto.
2.  Copia los scripts de `setup/` y `utils_general.py` a `scripts/`.
3.  Desde la raíz del proyecto, ejecuta `python -m scripts.setup.s00_main_initial_setup` para crear la estructura de archivos y el entorno virtual (`.venv/`).
4.  Inicializa Git (`git init`, `git branch -M main`), haz el primer commit.
5.  Autentica con GitHub CLI (`gh auth login`) y crea/configura el repositorio remoto usando `python -m scripts.setup.s03_setup_github_repo`. Haz push.
6.  Autentica con Google Cloud SDK (`gcloud auth login`, `gcloud auth application-default login`) y configura tu proyecto (`gcloud config set project YOUR_PROJECT_ID`). Verifica con `python -m scripts.setup.s04_gcloud_auth_setup`.
7.  Crea y configura `PROJECT_ROOT/.env` y `PROJECT_ROOT/requirements.txt` (solo define las dependencias por ahora).

### Fase 1: Infraestructura con Terraform e Instalación de Dependencias
1.  Activa el entorno virtual: `.\.venv\Scripts\activate` (Windows) o `source .venv/bin/activate` (Linux/macOS).
2.  Instala las dependencias: `pip install -r requirements.txt`.
3.  Completa los archivos de Terraform en la carpeta `terraform/`.
4.  Completa los scripts en `scripts/terraform_management/`.
5.  Ejecuta en orden (desde la raíz del proyecto, con el venv activado):
    *   `python -m scripts.terraform_management.tf_init_validate`
    *   `python -m scripts.terraform_management.tf_plan` (revisa el plan)
    *   `python -m scripts.terraform_management.tf_apply` (confirma)

### Fase 2: Configuración Específica de GCP y Datos
1.  Asegúrate de que el venv esté activado y las dependencias instaladas.
2.  Define tus credenciales de Alpaca en el archivo `.env`.
3.  Completa los scripts en `scripts/config_gcp/` y `scripts/data/`.
4.  Ejecuta el orquestador (desde la raíz del proyecto, con el venv activado):
    *   `python -m scripts.config_gcp.s00_main_gcp_config`
5.  Configura los secretos `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, y `GCP_SERVICE_ACCOUNT_EMAIL` en tu repositorio de GitHub (Settings > Secrets and variables > Actions).

### Fase 3: Desarrollo de la Aplicación y CI/CD
1.  Desarrolla el código de tu aplicación en la carpeta `app/`.
2.  Crea/completa tu `Dockerfile`.
3.  Crea/completa tu workflow de GitHub Actions en `.github/workflows/`.
4.  Haz push a tu rama principal para disparar el despliegue.

## Variables de Entorno

La aplicación y los scripts utilizan variables de entorno definidas en un archivo `.env` en la raíz del proyecto (copia `.env.example` a `.env`). Las principales son:

-   `GOOGLE_CLOUD_PROJECT`: ID de tu proyecto GCP.
-   `GCP_REGION`: Región principal de GCP (ej. `us-central1`, 'nam5').
-   `APP_SA_NAME`: Nombre corto de la Service Account de la aplicación (ej. `data-ingestion-ms-sa`).
-   `WIF_POOL_ID_SUFFIX`: Sufijo para el Workload Identity Pool ID (ej. `001`).
-   `GITHUB_REPO_OWNER`: Tu nombre de usuario u organización en GitHub.
-   `GITHUB_REPO_NAME`: Nombre de tu repositorio en GitHub.
-   `ALPACA_API_KEY_ID`: Tu API Key ID de Alpaca.
-   `ALPACA_SECRET_KEY`: Tu Secret Key de Alpaca.
-   `ALPACA_PAPER`: `true` o `false` para usar la API de paper trading o live.
-   `FETCH_TIMEFRAME_STR`: Timeframe para Alpaca (ej. `Day`, `Hour`).
-   `FETCH_DAYS_HISTORY`: Número de días de historial a obtener.
-   `SCHEDULE_TRIGGER`: Tipo de trigger para APScheduler (`interval` o `cron`).
-   `SCHEDULE_MINUTES` / `SCHEDULE_HOUR` / `SCHEDULE_MINUTE`: Parámetros para el scheduler.
-   `FIRESTORE_PROVIDERS_COLLECTION`, `FIRESTORE_ASSETS_COLLECTION`: Nombres de colecciones en Firestore.
-   `PUBSUB_HISTORICAL_DATA_TOPIC_ID`: ID del tópico de Pub/Sub.

**Nota:** Para el despliegue en Cloud Run, las variables sensibles como las de Alpaca se gestionarán a través de Google Secret Manager y se montarán como variables de entorno en el servicio Cloud Run.

## Scripts Principales

-   **`scripts/setup/s00_main_initial_setup.py`**: Orquestador para la creación inicial de la estructura y el venv.
-   **`scripts/terraform_management/`**: Scripts para ejecutar `terraform init, validate, plan, apply`.
-   **`scripts/config_gcp/s00_main_gcp_config.py`**: Orquestador para configurar permisos de SA, secretos de Alpaca en Secret Manager, Workload Identity Federation y poblar Firestore.
-   **`scripts/data/seed_firestore.py`**: Puebla Firestore con datos iniciales (proveedores, activos).

## Ejecución Local de la Aplicación

(Asumiendo que has configurado tus credenciales de Alpaca y GCP localmente, y has poblado Firestore)

1.  Activa el entorno virtual: `.\.venv\Scripts\activate`
2.  Asegúrate de que las variables de entorno estén disponibles (cargadas desde `.env` o configuradas en tu sistema).
3.  Ejecuta Uvicorn desde la raíz del proyecto:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    La aplicación estará disponible en `http://localhost:8000`.

## Despliegue

El despliegue se realiza automáticamente a través de GitHub Actions cuando se hace push a la rama principal (o la rama configurada en el workflow). El workflow:
1.  Se autentica en GCP usando Workload Identity Federation.
2.  Construye la imagen Docker.
3.  Sube la imagen a Google Artifact Registry.
4.  Despliega la nueva imagen en Google Cloud Run, configurando las variables de entorno y montando secretos desde Secret Manager.

## Contribuciones

(TODO: Especificar cómo otros pueden contribuir, si aplica)

## Licencia

(TODO: Especificar la licencia del proyecto, ej. MIT, Apache 2.0, o dejar en blanco si es privado)

---
```



