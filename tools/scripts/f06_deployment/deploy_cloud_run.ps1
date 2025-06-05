# Script PowerShell para desplegar en Cloud Run
param (
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "us-central1"
)

# Verificar ProjectId
if (-not $ProjectId) {
    Write-Error "PROJECT_ID no está definido. Define la variable de entorno PROJECT_ID o pásalo como parámetro."
    exit 1
}

# Obtener el directorio raíz del proyecto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Get-Item $scriptPath).Parent.Parent.Parent.FullName
$serviceDir = Join-Path $projectRoot "service"

# Verificar que estamos en el directorio correcto
if (-not (Test-Path (Join-Path $serviceDir "Dockerfile"))) {
    Write-Error "No se encontró Dockerfile en $serviceDir"
    exit 1
}

$serviceName = "data-ingestion-pt-ms"
$imageName = "gcr.io/$ProjectId/$serviceName"

try {
    Write-Host "`n=== Desplegando en Cloud Run ===" -ForegroundColor Cyan
    
    # Cambiar al directorio del servicio
    Push-Location $serviceDir
    
    # Construir la imagen
    Write-Host "`nConstruyendo imagen Docker..." -ForegroundColor Yellow
    $buildResult = gcloud builds submit --tag $imageName
    if ($LASTEXITCODE -ne 0) {
        throw "Error al construir la imagen"
    }
    
    # Desplegar en Cloud Run
    Write-Host "`nDesplegando en Cloud Run..." -ForegroundColor Yellow
    $deployResult = gcloud run deploy $serviceName `
        --image $imageName `
        --platform managed `
        --region $Region `
        --allow-unauthenticated
    if ($LASTEXITCODE -ne 0) {
        throw "Error al desplegar en Cloud Run"
    }
    
    Write-Host "`n✅ Despliegue completado exitosamente" -ForegroundColor Green
    
} catch {
    Write-Host "`n❌ Error durante el despliegue: $_" -ForegroundColor Red
    exit 1
} finally {
    # Volver al directorio original
    Pop-Location
}