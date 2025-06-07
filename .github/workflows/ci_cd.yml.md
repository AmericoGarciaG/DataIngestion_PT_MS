ci_cd.yml
Propósito: Este workflow de GitHub Actions automatiza el proceso de Integración Continua (CI) y Despliegue Continuo (CD) para la aplicación de servicio. Cuando se realiza un push a la rama main, el workflow se encarga de:

Construir una imagen Docker de la aplicación.
Autenticarse con Google Cloud Platform (GCP) usando Workload Identity Federation.
Subir la imagen Docker a Google Artifact Registry (GAR).
Desplegar la nueva imagen en Google Cloud Run, configurando variables de entorno y secretos necesarios.
Funcionamiento Principal:

1. Disparador (on):

El workflow se activa automáticamente cada vez que hay un push de commits a la rama main del repositorio.
2. Variables de Entorno Globales (env): Estas variables están disponibles para todos los jobs y steps del workflow.

GCP_PROJECT_ID: El ID del proyecto de Google Cloud. Se obtiene de los secretos de GitHub (secrets.GCP_PROJECT_ID).
GAR_LOCATION: La ubicación del repositorio de Artifact Registry (ej. us-central1). Utiliza una variable de GitHub (vars.GAR_LOCATION) con un valor predeterminado.
SERVICE_NAME: El nombre del servicio en Cloud Run. Utiliza una variable de GitHub (vars.SERVICE_NAME) con un valor predeterminado.
IMAGE_NAME_BASE: El nombre base para la imagen Docker. Utiliza una variable de GitHub (vars.SERVICE_NAME) con un valor predeterminado, coincidiendo con el nombre del servicio.
3. Job: build-and-deploy: Este es el único job definido en el workflow.

name: Build and Deploy: Nombre descriptivo del job.
runs-on: ubuntu-latest: Especifica que el job se ejecutará en la última versión disponible de un ejecutor (runner) de Ubuntu proporcionado por GitHub.
permissions: Define los permisos que el token GITHUB_TOKEN (proporcionado al workflow) tendrá:
contents: 'read': Permiso para leer el contenido del repositorio (necesario para el checkout).
id-token: 'write': Permiso para solicitar un token de identidad OIDC (OpenID Connect), necesario para Workload Identity Federation con GCP.
4. Pasos (steps) dentro del Job build-and-deploy:

plaintext
*   **`Checkout code`:**
    *   `uses: actions/checkout@v4`: Utiliza la acción oficial `checkout` para descargar el código fuente del repositorio en el ejecutor del workflow.

*   **`Authenticate to Google Cloud`:**
    *   `id: 'auth'`: Asigna un ID a este paso para que sus outputs puedan ser referenciados.
    *   `uses: 'google-github-actions/auth@v2'`: Utiliza la acción oficial de Google para autenticarse con GCP.
    *   `with`: Parámetros para la acción:
        *   `workload_identity_provider`: El nombre completo del proveedor de Workload Identity Federation en GCP. Se obtiene de los secretos de GitHub (`secrets.GCP_WORKLOAD_IDENTITY_PROVIDER`).
        *   `service_account`: El email de la Service Account de GCP que será impersonada por el workflow. Se obtiene de los secretos de GitHub (`secrets.GCP_SERVICE_ACCOUNT_EMAIL`).

*   **`Set up Cloud SDK`:**
    *   `uses: 'google-github-actions/setup-gcloud@v2'`: Utiliza la acción oficial de Google para configurar la CLI de `gcloud`.
    *   `with`:
        *   `project_id: ${{ env.GCP_PROJECT_ID }}`: Establece el proyecto GCP predeterminado para los comandos `gcloud`.

*   **`Configure Docker for Artifact Registry`:**
    *   `run: gcloud auth configure-docker ${{ env.GAR_LOCATION }}-docker.pkg.dev --quiet`: Configura el cliente Docker para autenticarse con Artifact Registry en la ubicación especificada. Esto permite los comandos `docker push` y `docker pull` contra el repositorio de GAR.

*   **`Build and Tag Docker image`:**
    *   `id: docker_build`: Asigna un ID a este paso.
    *   `run`: Ejecuta un script de shell multi-línea:
        *   Construye la ruta completa de la imagen en Artifact Registry (`IMAGE_PATH`).
        *   Genera dos tags para la imagen y los guarda como outputs del paso usando `echo "KEY=VALUE" >> $GITHUB_OUTPUT`:
            *   `IMAGE_PATH_WITH_TAG_SHA`: Tag con el SHA del commit (`${IMAGE_PATH}:${{ github.sha }}`).
            *   `IMAGE_PATH_WITH_TAG_LATEST`: Tag como `latest` (`${IMAGE_PATH}:latest`).
        *   Ejecuta `docker build`:
            *   `-t "${IMAGE_PATH}:${{ github.sha }}" -t "${IMAGE_PATH}:latest"`: Etiqueta la imagen con ambos tags.
            *   `-f service/Dockerfile`: Especifica la ruta al Dockerfile.
            *   `service/`: Especifica el contexto de construcción de Docker (el directorio `service/`).

*   **`Push Docker image to Artifact Registry`:**
    *   `run`: Ejecuta un script de shell multi-línea:
        *   `docker push ${{ steps.docker_build.outputs.IMAGE_PATH_WITH_TAG_SHA }}`: Sube la imagen con el tag SHA al Artifact Registry.
        *   `docker push ${{ steps.docker_build.outputs.IMAGE_PATH_WITH_TAG_LATEST }}`: Sube la imagen con el tag `latest` al Artifact Registry.

*   **`Deploy to Cloud Run`:**
    *   `id: 'deploy'`: Asigna un ID a este paso.
    *   `uses: 'google-github-actions/deploy-cloudrun@v2'`: Utiliza la acción oficial de Google para desplegar en Cloud Run.
    *   `with`: Parámetros para la acción:
        *   `service: ${{ env.SERVICE_NAME }}`: Nombre del servicio en Cloud Run.
        *   `region: ${{ env.GAR_LOCATION }}`: Región donde está el servicio de Cloud Run (asume que es la misma que GAR_LOCATION).
        *   `image: ${{ steps.docker_build.outputs.IMAGE_PATH_WITH_TAG_SHA }}`: Especifica la imagen a desplegar (la versionada con el SHA del commit).
        *   `env_vars`: Define las variables de entorno para el servicio de Cloud Run. Los valores se toman de las "Repository Variables" de GitHub (`vars.*`) con valores predeterminados si no están definidas. Incluye:
            *   `GOOGLE_CLOUD_PROJECT_ID`
            *   `ALPACA_PAPER`
            *   `ALPACA_ASSET_SYMBOL`
            *   `FETCH_TIMEFRAME_STR`
            *   `FETCH_DAYS_HISTORY`
            *   `SCHEDULE_TRIGGER`, `SCHEDULE_HOUR`, `SCHEDULE_MINUTE`
            *   `PUBSUB_TOPIC_NAME`
            *   `FIRESTORE_PROVIDERS_COLLECTION`, `FIRESTORE_ASSETS_COLLECTION`
        *   `secrets`: Monta secretos de Google Secret Manager como variables de entorno en Cloud Run.
            *   `ALPACA_API_KEY_ID=ALPACA_API_KEY_ID:latest`: Mapea el secreto `ALPACA_API_KEY_ID` (versión `latest`) de Secret Manager a la variable de entorno `ALPACA_API_KEY_ID` en Cloud Run.
            *   `ALPACA_SECRET_KEY=ALPACA_SECRET_KEY:latest`: Similar para la clave secreta.
        *   `flags: "--service-account ${{ secrets.GCP_SERVICE_ACCOUNT_EMAIL }} --allow-unauthenticated"`: Flags adicionales para el despliegue:
            *   `--service-account`: Especifica la Service Account que utilizará la revisión de Cloud Run.
            *   `--allow-unauthenticated`: Permite invocaciones no autenticadas al servicio de Cloud Run.

*   **`Show deployed service URL`:**
    *   `if: steps.deploy.outputs.url`: Este paso solo se ejecuta si el paso de despliegue (`steps.deploy`) tuvo un output `url` (es decir, el despliegue fue exitoso y generó una URL).
    *   `run: echo "Service deployed at: ${{ steps.deploy.outputs.url }}"`: Imprime la URL del servicio desplegado en los logs del workflow.
Entradas (Secrets y Variables de GitHub):

Secrets de Repositorio (secrets.*):
GCP_PROJECT_ID: ID del proyecto GCP.
GCP_WORKLOAD_IDENTITY_PROVIDER: Nombre del proveedor de Workload Identity Federation.
GCP_SERVICE_ACCOUNT_EMAIL: Email de la Service Account de GCP a impersonar.
Variables de Repositorio (vars.*):
GAR_LOCATION: Ubicación de Artifact Registry y Cloud Run.
SERVICE_NAME: Nombre del servicio en Cloud Run.
ARTIFACT_REGISTRY_REPO_NAME: Nombre del repositorio en Artifact Registry.
ALPACA_PAPER, ALPACA_ASSET_SYMBOL, etc.: Variables de configuración de la aplicación.
Salidas y Efectos Secundarios:

Construye y publica una imagen Docker en Artifact Registry.
Despliega una nueva revisión del servicio en Cloud Run.
Imprime la URL del servicio desplegado en los logs.
Mejores Prácticas y Consideraciones:

Workload Identity Federation: El uso de WIF es la forma recomendada y más segura para que GitHub Actions se autentique con GCP, ya que evita la necesidad de exportar y gestionar claves de Service Account de larga duración.
Tagging de Imágenes:
Etiquetar con el SHA del commit (github.sha) asegura que cada despliegue utilice una imagen inmutable y versionada.
Etiquetar con latest es una convención común, pero para los despliegues se prefiere el tag SHA para mayor trazabilidad y la capacidad de revertir a una versión específica.
Variables vs. Secretos:
Usar secrets para información sensible (credenciales, claves API).
Usar vars para configuración no sensible que puede variar entre entornos o despliegues.
Permisos de Cloud Run (--allow-unauthenticated): Este flag hace que el servicio sea públicamente accesible. Si el servicio no necesita ser público, se debe omitir este flag y configurar la autenticación IAM para Cloud Run.
Idempotencia: Las acciones de deploy-cloudrun y docker push son generalmente idempotentes.
Contexto de Docker Build: Es importante que el contexto (service/) y la ruta al Dockerfile (-f service/Dockerfile) sean correctos para que la imagen se construya como se espera.
Revisión de Cambios: Dado que este workflow despliega directamente a main, es crucial tener un proceso de revisión de código (Pull Requests) antes de fusionar a main para evitar despliegues no deseados o con errores. Para entornos más complejos, se podrían usar ramas de staging o develop con workflows separados