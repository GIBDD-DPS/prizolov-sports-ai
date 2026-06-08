# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.16 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
# Creates deploy-amvera.zip WITHOUT venv/node_modules for manual Amvera upload.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = Join-Path $Root "deploy-amvera.zip"

if (Test-Path $Out) { Remove-Item $Out -Force }

$ExcludeDirs = @(
    "venv", ".venv", "node_modules", ".git", ".github", "__pycache__",
    "frontend\node_modules", "frontend\.next", "backend\venv", ".idea", ".vscode"
)

Write-Host "Creating Amvera deploy zip (no venv)..."
Write-Host "Root: $Root"

# Use tar if available (Windows 10+), exclude patterns
Push-Location $Root
try {
    $items = Get-ChildItem -Force | Where-Object {
        $name = $_.Name
        $name -notin @("venv", ".venv", "node_modules", ".git", "deploy-amvera.zip")
    }
    Compress-Archive -Path @(
        "amvera.yaml", "amvera.yml", "Dockerfile", "requirements.txt", "VERSION",
        "backend", "shared", "scripts", "docs", "README.md", "CHANGELOG.md", ".env.example"
    ) -DestinationPath $Out -Force
    Write-Host "OK: $Out"
    Write-Host "Upload this zip to Amvera (or use GitHub main instead)."
} finally {
    Pop-Location
}
