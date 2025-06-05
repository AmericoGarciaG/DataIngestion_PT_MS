#!/usr/bin/env powershell
# _restore_files.ps1

# =============================================================================
# Project Restoration Script
# This script restores the project structure and files from a backup
# based on the project_map.json file located in the same directory.
#
# IMPORTANT:
# 1. Ensure this script is run from the 'tools/_2_restore/' directory.
# 2. Update the $dest_root_dir variable below to your desired project root path.
# =============================================================================

# Define root destination directory
$dest_root_dir = "G:\Mi unidad\01_PROYECTOS\02_POS\DataIngestion_PT_MS"  # <--- CAMBIA ESTO A TU DESTINO DESEADO

# Get the directory where this script is located and set up paths
$script_path = $PSScriptRoot
$tools_dir = Split-Path $script_path -Parent
$map_file = Join-Path $tools_dir "project_map.json"
$backup_files_dir = Join-Path $script_path "backed_up_files"

# Initialize counters
$uniqueDirectoriesDefinedInMap = 0
$uniqueDirectoriesNewlyCreated = 0
$uniqueDirectoriesFoundExisted = 0
$otherDirectoriesEnsured = 0
$filesCopied = 0
$filesSkippedDueToExistence = 0
$filesSkippedOrFailedOther = 0

# Function to create directory if it doesn't exist
function EnsureDirectory {
    param(
        [string]$path,
        [bool]$isFromInitialList = $false
    )
    if ($isFromInitialList) {
        $script:uniqueDirectoriesDefinedInMap++
    }

    if (-not (Test-Path $path -PathType Container)) {
        try {
            Write-Verbose "Attempting to create directory: $path"
            New-Item -ItemType Directory -Path $path -Force -ErrorAction Stop | Out-Null
            Write-Host "[OK] Created directory: $path"
            if ($isFromInitialList) {
                $script:uniqueDirectoriesNewlyCreated++
            } else {
                $script:otherDirectoriesEnsured++
            }
        } catch {
            Write-Error "Failed to create directory: $path. Error: $($_.Exception.Message)"
        }
    } else {
        if ($isFromInitialList) {
            $script:uniqueDirectoriesFoundExisted++
        }
    }
}

# --- Main execution ---
Write-Host "Starting project restoration using '$($map_file.Split('\')[-1])'..." -ForegroundColor Green
Write-Host "Source backup files from: '$($backup_files_dir.Split('\')[-1])'"
Write-Host "Destination project root: '$dest_root_dir'"
Write-Host "--------------------------------------------------"

# 0. Load mapping data
# ...existing code...
if (-not (Test-Path $map_file -PathType Leaf)) { Write-Error "Mapping file not found: $map_file"; exit 1 }
try { $projectData = Get-Content $map_file -Raw | ConvertFrom-Json -ErrorAction Stop }
catch { Write-Error "Failed to parse JSON mapping file '$map_file'. Error: $($_.Exception.Message)"; exit 1 }

# 0.1 Ensure destination root exists
Write-Host "`nStep 0.1: Ensuring destination root directory exists..." -ForegroundColor Cyan
EnsureDirectory -path $dest_root_dir

# 1. Create directory structure from 'directories_to_create'
Write-Host "`nStep 1: Creating directory structure from 'directories_to_create'..." -ForegroundColor Cyan
# ...existing code...
if ($null -ne $projectData.directories_to_create -and $projectData.directories_to_create.Count -gt 0) {
    foreach ($dir_relative_path in $projectData.directories_to_create) {
        if (-not [string]::IsNullOrWhiteSpace($dir_relative_path)) {
            $fullPath = Join-Path $dest_root_dir $dir_relative_path
            EnsureDirectory -path $fullPath -isFromInitialList $true
        }
    }
    Write-Host "[DONE] Directory structure (from 'directories_to_create') creation/verification complete."
} else { Write-Warning "No 'directories_to_create' array found in JSON. Skipping."}


# 2. Copy files from backup to their destinations based on 'file_mappings'
Write-Host "`nStep 2: Copying files from backup..." -ForegroundColor Cyan
if ($null -ne $projectData.file_mappings) {
    $fileMappingObject = $projectData.file_mappings
    $fileMappingKeys = $fileMappingObject.PSObject.Properties | ForEach-Object { $_.Name }

    if ($fileMappingKeys.Count -eq 0) {
        Write-Warning "No file mappings found in JSON under 'file_mappings'. Skipping file copy."
    } else {
        foreach ($backupFileNameInJson in $fileMappingKeys) {
            $destinationRelativePathWithFileName = $fileMappingObject.$backupFileNameInJson
            $sourceFileFullPath = Join-Path $backup_files_dir $backupFileNameInJson

            if (-not (Test-Path $sourceFileFullPath -PathType Leaf)) {
                Write-Warning "[SOURCE NOT FOUND] File '$backupFileNameInJson' not in '$($backup_files_dir.Split('\')[-1])'. Skipping."
                $filesSkippedOrFailedOther++
                continue
            }

            $fullDestinationPathAndName = Join-Path $dest_root_dir $destinationRelativePathWithFileName
            $destinationDirOnly = Split-Path -Path $fullDestinationPathAndName -Parent

            EnsureDirectory -path $destinationDirOnly -isFromInitialList $false

            # --- VERIFICACIÓN ANTES DE COPIAR ---
            if (Test-Path $fullDestinationPathAndName -PathType Leaf) {
                Write-Host "[SKIPPED] File '$destinationRelativePathWithFileName' already exists. No overwrite."
                $script:filesSkippedDueToExistence++
                continue
            }
            # --- FIN DE VERIFICACIÓN ---

            try {
                Copy-Item -Path $sourceFileFullPath -Destination $fullDestinationPathAndName -Force -ErrorAction Stop
                Write-Host "[COPIED] '$backupFileNameInJson' (from $($backup_files_dir.Split('\')[-1])) to '$destinationRelativePathWithFileName'"
                $filesCopied++
            } catch {
                Write-Error "Failed to copy '$sourceFileFullPath' to '$fullDestinationPathAndName'. Error: $($_.Exception.Message)"
                $filesSkippedOrFailedOther++
            }
        }
        Write-Host "[DONE] File copying complete."
    }
} else {
    Write-Warning "No 'file_mappings' object found in JSON or it's empty. Skipping file copy."
}

# --- Resumen Final ---
Write-Host "`n--------------------------------------------------"
Write-Host "Project Restoration Summary:" -ForegroundColor Yellow
Write-Host "  Directories defined in 'directories_to_create':"
Write-Host "    - Total unique in map: $uniqueDirectoriesDefinedInMap"
Write-Host "    - Newly created: $uniqueDirectoriesNewlyCreated"
Write-Host "    - Already existed: $uniqueDirectoriesFoundExisted"
if ($otherDirectoriesEnsured -gt 0) {
    Write-Host "  Additional parent directories for files created/verified: $otherDirectoriesEnsured"
}
Write-Host "  Files from 'file_mappings':"
Write-Host "    - Successfully copied/restored: $filesCopied"
Write-Host "    - Skipped (already existed at destination): $filesSkippedDueToExistence"
Write-Host "    - Skipped (source not found) or failed to copy: $filesSkippedOrFailedOther"
Write-Host "--------------------------------------------------"
Write-Host "Project restoration process finished!" -ForegroundColor Green