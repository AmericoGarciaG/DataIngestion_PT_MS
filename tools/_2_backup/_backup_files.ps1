#!/usr/bin/env powershell
# _backup_files.ps1

# =============================================================================
# Project Backup Script
# This script backs up the project files to a backup directory
# based on the project_map.json file located in the tools directory.
#
# IMPORTANT:
# 1. Ensure this script is run from the 'tools/_2_backup/' directory.
# 2. Update the $project_root_dir variable below to your project root path.
# =============================================================================

# Define project root directory
$project_root_dir = "G:\Mi unidad\01_PROYECTOS\02_POS\DataIngestion_PT_MS"  # <--- CAMBIA ESTO A TU PROYECTO

# Get the directory where this script is located and set up paths
$script_path = $PSScriptRoot
$backup_files_dir = Join-Path $script_path "backup_files"
$tools_dir = Split-Path $script_path -Parent
$map_file = Join-Path $tools_dir "project_map.json"

# Initialize counters
$filesBackedUp = 0
$filesSkippedDueToExistence = 0
$filesSkippedOrFailedOther = 0
$backupDirsCreated = 0

# Function to create directory if it doesn't exist
function EnsureDirectory {
    param([string]$path)
    
    if (-not (Test-Path $path -PathType Container)) {
        try {
            Write-Verbose "Attempting to create directory: $path"
            New-Item -ItemType Directory -Path $path -Force -ErrorAction Stop | Out-Null
            Write-Host "[OK] Created directory: $path"
            $script:backupDirsCreated++
        } catch {
            Write-Error "Failed to create directory: $path. Error: $($_.Exception.Message)"
        }
    }
}

# --- Main execution ---
Write-Host "Starting project backup using '$($map_file.Split('\')[-1])'..." -ForegroundColor Green
Write-Host "Source project root: '$project_root_dir'"
Write-Host "Destination backup directory: '$($backup_files_dir.Split('\')[-1])'"
Write-Host "--------------------------------------------------"

# 0. Load mapping data
if (-not (Test-Path $map_file -PathType Leaf)) { 
    Write-Error "Mapping file not found: $map_file"
    exit 1 
}
try { 
    $projectData = Get-Content $map_file -Raw | ConvertFrom-Json -ErrorAction Stop 
}
catch { 
    Write-Error "Failed to parse JSON mapping file '$map_file'. Error: $($_.Exception.Message)"
    exit 1 
}

# 0.1 Ensure backup directory exists
Write-Host "`nStep 0.1: Ensuring backup directory exists..." -ForegroundColor Cyan
EnsureDirectory -path $backup_files_dir

# 1. Copy files from project to backup based on 'file_mappings'
Write-Host "`nStep 1: Backing up files..." -ForegroundColor Cyan
if ($null -ne $projectData.file_mappings) {
    $fileMappingObject = $projectData.file_mappings
    $fileMappingKeys = $fileMappingObject.PSObject.Properties | ForEach-Object { $_.Name }

    if ($fileMappingKeys.Count -eq 0) {
        Write-Warning "No file mappings found in JSON under 'file_mappings'. Nothing to backup."
    } else {
        foreach ($backupFileNameInJson in $fileMappingKeys) {
            $sourceRelativePathWithFileName = $fileMappingObject.$backupFileNameInJson
            $sourceFileFullPath = Join-Path $project_root_dir $sourceRelativePathWithFileName
            $destinationFullPath = Join-Path $backup_files_dir $backupFileNameInJson

            if (-not (Test-Path $sourceFileFullPath -PathType Leaf)) {
                Write-Warning "[SOURCE NOT FOUND] File '$sourceRelativePathWithFileName' not in project. Skipping."
                $filesSkippedOrFailedOther++
                continue
            }

            # Ensure backup subdirectory exists if needed
            $destinationDirOnly = Split-Path -Path $destinationFullPath -Parent
            if ($destinationDirOnly -ne $backup_files_dir) {
                EnsureDirectory -path $destinationDirOnly
            }

            # --- VERIFICACIÓN ANTES DE COPIAR ---
            if (Test-Path $destinationFullPath -PathType Leaf) {
                $sourceHash = Get-FileHash -Path $sourceFileFullPath -Algorithm SHA256
                $destHash = Get-FileHash -Path $destinationFullPath -Algorithm SHA256
                
                if ($sourceHash.Hash -eq $destHash.Hash) {
                    Write-Host "[SKIPPED] File '$backupFileNameInJson' already backed up and identical. Skipping."
                    $filesSkippedDueToExistence++
                    continue
                }
            }
            # --- FIN DE VERIFICACIÓN ---

            try {
                Copy-Item -Path $sourceFileFullPath -Destination $destinationFullPath -Force -ErrorAction Stop
                Write-Host "[BACKED UP] '$sourceRelativePathWithFileName' to '$backupFileNameInJson'"
                $filesBackedUp++
            } catch {
                Write-Error "Failed to backup '$sourceFileFullPath' to '$destinationFullPath'. Error: $($_.Exception.Message)"
                $filesSkippedOrFailedOther++
            }
        }
        Write-Host "[DONE] File backup complete."
    }
} else {
    Write-Warning "No 'file_mappings' object found in JSON or it's empty. Nothing to backup."
}

# --- Resumen Final ---
Write-Host "`n--------------------------------------------------"
Write-Host "Project Backup Summary:" -ForegroundColor Yellow
Write-Host "  Backup directories:"
Write-Host "    - Created/verified: $backupDirsCreated"
Write-Host "  Files:"
Write-Host "    - Successfully backed up: $filesBackedUp"
Write-Host "    - Skipped (identical backup existed): $filesSkippedDueToExistence"
Write-Host "    - Skipped (source not found) or failed: $filesSkippedOrFailedOther"
Write-Host "--------------------------------------------------"
Write-Host "Project backup process finished!" -ForegroundColor Green
