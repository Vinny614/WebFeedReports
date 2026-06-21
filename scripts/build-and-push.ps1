<#
.SYNOPSIS
  Build and push the three service images to ACR, then publish sources.yaml.

.DESCRIPTION
  Run AFTER 'az deployment group create' has provisioned infrastructure, so the
  ACR and storage account exist. Uses 'az acr build' (no local Docker required)
  and Entra auth for the blob upload (no keys).

.EXAMPLE
  ./scripts/build-and-push.ps1 -ResourceGroup wfr-rg -Registry wfrdevacr -StorageAccount wfrdevst
#>
param(
  [Parameter(Mandatory = $true)][string]$ResourceGroup,
  [Parameter(Mandatory = $true)][string]$Registry,
  [Parameter(Mandatory = $true)][string]$StorageAccount,
  [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Building API image..."
az acr build --registry $Registry --image "webfeed-api:$Tag" `
  --file "$repoRoot/apps/api/Dockerfile" $repoRoot

Write-Host "Building worker image..."
az acr build --registry $Registry --image "webfeed-worker:$Tag" `
  --file "$repoRoot/apps/worker/Dockerfile" $repoRoot

Write-Host "Building frontend image..."
az acr build --registry $Registry --image "webfeed-frontend:$Tag" `
  --file "$repoRoot/apps/frontend/Dockerfile" $repoRoot

Write-Host "Publishing sources.yaml to Blob (Option B)..."
az storage blob upload `
  --account-name $StorageAccount `
  --auth-mode login `
  --container-name sources `
  --name sources.yaml `
  --file "$repoRoot/config/sources.yaml" `
  --overwrite

Write-Host "Done. Update infra/main.bicepparam image params to:"
Write-Host "  $Registry.azurecr.io/webfeed-api:$Tag"
Write-Host "  $Registry.azurecr.io/webfeed-worker:$Tag"
Write-Host "  $Registry.azurecr.io/webfeed-frontend:$Tag"
Write-Host "Then re-run the deployment to roll the images onto the container apps."
