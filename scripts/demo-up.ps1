<#
.SYNOPSIS
  Stand up the entire WebFeedReports demo with a single command.

.DESCRIPTION
  From a clean subscription this will:
    1. Create the resource group (if needed).
    2. Create the Azure Container Registry (if needed) so images can be built.
    3. Build + push the api, worker and frontend images with 'az acr build'
       (no local Docker required).
    4. Deploy all infrastructure (Bicep) wired to those images.
    5. Publish config/sources.yaml to Blob Storage.
    6. Kick off an initial ingest so search/reports have content.
    7. Print the live demo URL.

  Everything uses Managed Identity / Entra auth — no keys. namePrefix and
  location are read from infra/main.bicepparam so there is a single source of
  truth for resource names.

.EXAMPLE
  ./scripts/demo-up.ps1
  ./scripts/demo-up.ps1 -ResourceGroup rg-webscrape -Tag demo
#>
param(
  [string]$ResourceGroup = "rg-webscrape",
  [string]$Tag = "demo",
  [string]$ParamFile = "infra/main.bicepparam",
  [switch]$SkipIngest
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$paramPath = Join-Path $repoRoot $ParamFile

# --- Read namePrefix + location from the bicepparam (single source of truth) ---
$paramText = Get-Content $paramPath -Raw
$namePrefix = ([regex]::Match($paramText, "param\s+namePrefix\s*=\s*'([^']+)'")).Groups[1].Value
$location = ([regex]::Match($paramText, "param\s+location\s*=\s*'([^']+)'")).Groups[1].Value
if (-not $namePrefix -or -not $location) {
  throw "Could not read namePrefix/location from $ParamFile."
}

# Derived resource names (must match the Bicep modules).
$acrName = ($namePrefix + "acr").ToLower().Replace("-", "")
$loginServer = "$acrName.azurecr.io"

$apiImage = "$loginServer/webfeed-api:$Tag"
$workerImage = "$loginServer/webfeed-worker:$Tag"
$frontendImage = "$loginServer/webfeed-frontend:$Tag"

Write-Host "=== WebFeedReports demo: UP ===" -ForegroundColor Cyan
Write-Host "  Resource group : $ResourceGroup"
Write-Host "  Name prefix    : $namePrefix"
Write-Host "  Location       : $location"
Write-Host "  Registry       : $loginServer"
Write-Host "  Image tag      : $Tag"
Write-Host ""

# --- 1. Resource group -------------------------------------------------------
Write-Host "[1/6] Ensuring resource group..." -ForegroundColor Yellow
az group create -n $ResourceGroup -l $location --tags SecurityControl=Ignore --output none

# --- 2. Container registry (needed before we can build) ----------------------
Write-Host "[2/6] Ensuring container registry '$acrName'..." -ForegroundColor Yellow
$acrExists = az acr show -n $acrName -g $ResourceGroup --query name -o tsv 2>$null
if (-not $acrExists) {
  az acr create -n $acrName -g $ResourceGroup --sku Basic --admin-enabled false --output none
}

# Helper: build an image and confirm it was pushed. On Windows the 'az acr build'
# log streamer can crash with a cp1252 UnicodeEncodeError (the bundled Python
# ignores PYTHONUTF8/PYTHONIOENCODING), but the server-side build still runs to
# completion. So we ignore the client crash, poll the ACR run to a terminal
# state, then verify the tag exists.
function Build-Image {
  param([string]$Repo, [string]$Dockerfile)
  Write-Host "      building $Repo`:$Tag ..."

  # Don't let a non-zero exit from the crashed log streamer abort the script.
  $PSNativeCommandUseErrorActionPreference = $false
  az acr build --registry $acrName --image "$Repo`:$Tag" --file (Join-Path $repoRoot $Dockerfile) $repoRoot *> $null

  # Wait for the most recent ACR run (this build) to reach a terminal state.
  $status = $null
  for ($i = 0; $i -lt 120; $i++) {
    Start-Sleep -Seconds 10
    $status = az acr task list-runs --registry $acrName --top 1 --query "[0].status" -o tsv 2>$null
    if ($status -in @("Succeeded", "Failed", "Canceled", "Error", "Timeout")) { break }
  }
  if ($status -ne "Succeeded") {
    throw "ACR build for $Repo`:$Tag did not succeed (status: $status). Check 'az acr task list-runs --registry $acrName'."
  }

  $tags = az acr repository show-tags --name $acrName --repository $Repo -o tsv 2>$null
  if ($tags -notcontains $Tag) {
    throw "Image $Repo`:$Tag was not pushed despite a successful run."
  }
}

# --- 3. Build + push images --------------------------------------------------
Write-Host "[3/6] Building and pushing images..." -ForegroundColor Yellow
Build-Image -Repo "webfeed-api" -Dockerfile "apps/api/Dockerfile"
Build-Image -Repo "webfeed-worker" -Dockerfile "apps/worker/Dockerfile"
Build-Image -Repo "webfeed-frontend" -Dockerfile "apps/frontend/Dockerfile"

# --- 4. Deploy infrastructure ------------------------------------------------
Write-Host "[4/6] Deploying infrastructure (this can take several minutes)..." -ForegroundColor Yellow
$outputs = az deployment group create `
  --resource-group $ResourceGroup `
  --template-file (Join-Path $repoRoot "infra/main.bicep") `
  --parameters namePrefix=$namePrefix location=$location `
  apiImage=$apiImage workerImage=$workerImage frontendImage=$frontendImage `
  --query properties.outputs -o json | ConvertFrom-Json

$frontendFqdn = $outputs.frontendFqdn.value
$storageName = $outputs.storageName.value
$frontendUrl = "https://$frontendFqdn"

# --- 5. Publish sources.yaml -------------------------------------------------
Write-Host "[5/6] Publishing config/sources.yaml to storage '$storageName'..." -ForegroundColor Yellow

# Shared-key access is disabled, so the uploader needs a Blob data-plane role.
# Grant the signed-in identity (user or service principal) Storage Blob Data
# Contributor on the account, then upload (retrying while RBAC propagates).
$principalId = az ad signed-in-user show --query id -o tsv 2>$null
if (-not $principalId) { $principalId = az account show --query user.name -o tsv }
$storageId = az storage account show -n $storageName -g $ResourceGroup --query id -o tsv
az role assignment create --assignee $principalId `
  --role "Storage Blob Data Contributor" --scope $storageId --output none 2>$null

$uploaded = $false
for ($i = 0; $i -lt 12 -and -not $uploaded; $i++) {
  try {
    az storage blob upload `
      --account-name $storageName `
      --auth-mode login `
      --container-name sources `
      --name sources.yaml `
      --file (Join-Path $repoRoot "config/sources.yaml") `
      --overwrite --output none 2>$null
    if ($LASTEXITCODE -eq 0) { $uploaded = $true; break }
  } catch { }
  Start-Sleep -Seconds 15   # wait for the role assignment to propagate
}
if (-not $uploaded) {
  throw "Could not upload sources.yaml (RBAC may still be propagating). Re-run the script."
}

# Publish report templates alongside sources (same container is provisioned by Bicep).
az storage blob upload `
  --account-name $storageName `
  --auth-mode login `
  --container-name report-templates `
  --name templates.yaml `
  --file (Join-Path $repoRoot "config/report_templates.yaml") `
  --overwrite --output none 2>$null
if ($LASTEXITCODE -eq 0) {
  Write-Host "      published report templates." -ForegroundColor Green
} else {
  Write-Host "      WARNING: could not upload report_templates.yaml." -ForegroundColor Red
}

# --- 6. Initial ingest -------------------------------------------------------
if ($SkipIngest) {
  Write-Host "[6/6] Skipping initial ingest (-SkipIngest)." -ForegroundColor Yellow
} else {
  Write-Host "[6/6] Triggering initial ingest..." -ForegroundColor Yellow
  $started = $false
  for ($attempt = 0; $attempt -lt 10 -and -not $started; $attempt++) {
    try {
      $ing = Invoke-RestMethod -Uri "$frontendUrl/api/sources/refresh" -Method Post -TimeoutSec 30
      $started = $true
    } catch {
      Start-Sleep -Seconds 10   # frontend/api revision may still be warming up
    }
  }
  if ($started) {
    Write-Host "      ingest job $($ing.job_id) queued; waiting for completion..."
    for ($i = 0; $i -lt 90; $i++) {
      Start-Sleep -Seconds 10
      try { $j = Invoke-RestMethod -Uri "$frontendUrl/api/jobs/ingest/$($ing.job_id)" -TimeoutSec 30 } catch { continue }
      if ($j.status -eq "succeeded") {
        if ($j.result_ref -eq "chunks=0") {
          Write-Host "      ingest finished but indexed 0 chunks — check sources.yaml / worker logs." -ForegroundColor Red
        } else {
          Write-Host "      ingest complete: $($j.result_ref)" -ForegroundColor Green
        }
        break
      }
      if ($j.status -eq "failed") { Write-Host "      ingest FAILED: $($j.error)" -ForegroundColor Red; break }
    }
  } else {
    Write-Host "      Could not reach the API to start ingest. Run it later from the Dashboard." -ForegroundColor Red
  }
}

Write-Host ""
Write-Host "=== Demo is live ===" -ForegroundColor Green
Write-Host "  $frontendUrl"
Write-Host ""
Write-Host "When you're done, tear it all down with:" -ForegroundColor Cyan
Write-Host "  ./scripts/demo-down.ps1 -ResourceGroup $ResourceGroup"
