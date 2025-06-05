# Project Structure Documentation

Este documento describe la estructura de directorios y archivos del proyecto DataIngestion_PT_MS.

## Estructura del Proyecto

```
DataIngestion_PT_MS/
├── service/                      # Todo lo relacionado con el microservicio
│   ├── app/                     # Código principal del microservicio
│   │   ├── __init__.py
│   │   ├── main.py             # Punto de entrada FastAPI
│   │   ├── alpaca_service.py   # Lógica de Alpaca
│   │   ├── config.py           # Configuración del servicio
│   │   └── gcp_clients.py      # Clientes de GCP
│   ├── tests/                  # Tests específicos del microservicio
│   │   ├── __init__.py
│   │   ├── test_alpaca_data.py
│   │   ├── test_alpaca_fetch.py
│   │   └── test_fetch.py
│   ├── Dockerfile              # Docker para el servicio
│   └── requirements.txt        # Dependencias del servicio
│
├── tools/                      # Herramientas de desarrollo y despliegue
│   ├── scripts/               # Scripts de gestión
│   │   ├── __init__.py
│   │   ├── docker-entrypoint.sh
│   │   ├── f02_manage_gcp_environment.py
│   │   ├── utils_general.py
│   │   ├── f00_files_setup/  # Scripts de configuración inicial
│   │   ├── f03_terraform_management/
│   │   ├── f04_gcp_setup/    # Configuración de GCP
│   │   ├── f05_data/         # Scripts de datos
│   │   └── f06_deployment/   # Scripts de despliegue
│   └── tests/                # Tests de integración y cliente
│       ├── __init__.py
│       ├── client_test.py
│       ├── read_firestore_bars.py
│       ├── requirements-test.txt
│       ├── run_client.ps1
│       └── run_fetch_test.ps1
│
├── terraform/                 # Configuración de infraestructura
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
│
└── docs/                     # Documentación del proyecto
    ├── API_Endpoints.md
    ├── Arquitectura.md
    ├── Guia_Configuracion_Proyecto.md
    └── Guia_Despliegue_Paso_A_Paso.md
```

## Root Directory (./)
- `README.md` - Documentación principal del proyecto, guía de inicio rápido.
- `.gitignore` - Especifica archivos y directorios a ignorar en Git.
- `.dockerignore` - Especifica archivos y directorios a ignorar al construir la imagen Docker.

## Service (service/)
Contiene todo el código y configuración del microservicio.
- `app/` - Código fuente de la aplicación.
  - `__init__.py`
  - `main.py` - Punto de entrada FastAPI.
  - `alpaca_service.py` - Lógica de negocio.
  - `config.py` - Configuración.
  - `gcp_clients.py` - Clientes GCP.
- `tests/` - Tests unitarios y funcionales del servicio.
  - `__init__.py`
  - `test_alpaca_data.py`
  - `test_alpaca_fetch.py`
  - `test_fetch.py`
- `Dockerfile` - Dockerfile para el servicio.
- `requirements.txt` - Dependencias del servicio.

## Tools (tools/)
Contiene herramientas de desarrollo, pruebas y despliegue.
- `scripts/` - Scripts de gestión y automatización.
  - `__init__.py`
  - `docker-entrypoint.sh`
  - `f02_manage_gcp_environment.py`
  - `utils_general.py`
  - `f00_files_setup/` - Configuración inicial.
  - `f03_terraform_management/` - Gestión de Terraform.
  - `f04_gcp_setup/` - Configuración de GCP.
  - `f05_data/` - Scripts de datos.
  - `f06_deployment/` - Scripts de despliegue.
- `tests/` - Tests de integración y cliente.
  - `__init__.py` - Inicializador del paquete `tests`.
  - `client_test.py` - Pruebas para el cliente de la API o interacciones cliente.
  - `read_firestore_bars.py` - Pruebas específicas para la lectura de datos de Firestore.
  - `requirements-test.txt` - Dependencias para ejecutar las pruebas.
  - `run_client.ps1` - Script para ejecutar el cliente de pruebas.
  - `run_fetch_test.ps1` - Script para ejecutar la prueba de fetch.

## Terraform (terraform/)
Configuraciones de Infraestructura como Código (IaC).
- `main.tf` - Configuración principal de Terraform (recursos).
- `outputs.tf` - Definiciones de salidas de Terraform.
- `variables.tf` - Definiciones de variables de Terraform.
- `versions.tf` - Especifica versiones de Terraform y proveedores.

## Docs (docs/)
Documentación del proyecto.
- `API_Endpoints.md`
- `Arquitectura.md`
- `Guia_Configuracion_Proyecto.md`
- `Guia_Despliegue_Paso_A_Paso.md`

## Development Configuration

### Devcontainer (.devcontainer/)
Directorio para la configuración del contenedor de desarrollo de VS Code.
- `devcontainer.json` - Configuración principal del contenedor de desarrollo.
- `Dockerfile` - Definición del Dockerfile específico para el entorno de desarrollo.

### GitHub Actions Workflows (.github/workflows/)
Directorio para los flujos de trabajo de CI/CD y otras automatizaciones con GitHub Actions.
- `ci.yml` - Flujo de trabajo para Integración Continua (ej: linters, tests unitarios en cada push/PR).
- `cd.yml` - Flujo de trabajo para Despliegue Continuo (ej: despliegue a Cloud Run tras merge a `main`).
- `tests.yml` - Flujo de trabajo dedicado para ejecutar pruebas automatizadas (puede ser parte de `ci.yml`).

### VSCode Workspace Settings (.vscode/)
Configuraciones específicas del espacio de trabajo para Visual Studio Code.
- `launch.json` - Configuraciones de depuración para ejecutar y depurar la aplicación.
- `settings.json` - Ajustes específicos del proyecto para VS Code (ej: formateador, linter).
- `tasks.json` - Definiciones de tareas personalizadas para VS Code (ej: ejecutar scripts).
- `extensions.json` - Extensiones recomendadas de VS Code para este proyecto.

### Internal Documentation Assets (tools/_2_restore/)
Recursos internos para la documentación o metadatos del proyecto.
- `backed_up_files/` - (Directorio) Copia de seguridad de archivos clave del proyecto.
- `project_map.json` - (Archivo) Define la estructura de directorios y el mapeo de archivos para la restauración.
- `_restore_files.ps1` - (Archivo) Script PowerShell para restaurar la estructura y archivos.
- `Project_Structure.md` - (Archivo) *Esta copia del archivo de estructura se usa para la herramienta de restauración.*

## Logs (logs/)
Directorio destinado a almacenar los archivos de logs generados por la aplicación.
*(Este directorio usualmente se añade al .gitignore y no se versiona su contenido).*

## Terraform Infrastructure (terraform/)
Configuraciones de Infraestructura como Código (IaC) usando Terraform.
- `main.tf` - Configuración principal de Terraform (recursos).
- `outputs.tf` - Definiciones de salidas de Terraform.
- `variables.tf` - Definiciones de variables de Terraform.
- `versions.tf` - Especifica versiones de Terraform y proveedores.

## Tests (tools/tests/)
Directorio para pruebas automatizadas.
- `__init__.py` - Inicializador del paquete `tests`.
- `client_test.py` - Pruebas para el cliente de la API o interacciones cliente.
- `read_firestore_bars.py` - Pruebas específicas para la lectura de datos de Firestore.
- `requirements-test.txt` - Dependencias para ejecutar las pruebas.
- `run_client.ps1` - Script para ejecutar el cliente de pruebas.
- `run_fetch_test.ps1` - Script para ejecutar la prueba de fetch.