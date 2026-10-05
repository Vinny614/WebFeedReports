<#
.SYNOPSIS
  Tear down the entire WebFeedReports demo.

.DESCRIPTION
  Deletes the resource group (removing every resource and stopping all cost),
  then purges the soft-deleted Azure OpenAI account so the same name can be
  redeployed immediately. Azure AI Search and the registry name are released as
  soon as the group is gone.

  namePrefix + location are read from infra/main.bicepparam so the OpenAI
  account name is derived correctly.

.EXAMPLE
  ./scripts/demo-down.ps1
  ./scripts/demo-down.ps1 -ResourceGroup rg-webscrape
  ./scripts/demo-down.ps1 -ResourceGroup rg-webscrape -Location eastus2
#>
param(
  [string]$ResourceGroup = "rg-webscrape",
  [string]$ParamFile = "infra/main.bicepparam",
  [string]$Location
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$paramPath = Join-Path $repoRoot $ParamFile

$paramText = Get-Content $paramPath -Raw
$namePrefix = ([regex]::Match($paramText, "param\s+namePrefix\s*=\s*'([^']+)'")).Groups[1].Value
$configuredLocation = ([regex]::Match($paramText, "param\s+location\s*=\s*'([^']+)'")).Groups[1].Value
if (-not $Location) { $Location = $configuredLocation }
$openaiName = "$namePrefix-openai"

Write-Host "=== WebFeedReports demo: DOWN ===" -ForegroundColor Cyan
Write-Host "  Resource group : $ResourceGroup"
Write-Host "  OpenAI account : $openaiName ($Location)"
Write-Host ""

$exists = az group exists -n $ResourceGroup -o tsv
if ($exists -ne "true") {
  Write-Host "Resource group '$ResourceGroup' does not exist. Nothing to do." -ForegroundColor Yellow
  return
}

Write-Host "[1/2] Deleting resource group '$ResourceGroup' (waiting for completion)..." -ForegroundColor Yellow
az group delete -n $ResourceGroup --yes --output none

# Azure OpenAI / Cognitive Services accounts are soft-deleted with the group.
# Purge so a future demo-up can recreate the same name without conflict.
Write-Host "[2/2] Purging soft-deleted OpenAI account (if present)..." -ForegroundColor Yellow
$deletedOpenAI = az cognitiveservices account list-deleted `
  --query "[?name=='$openaiName' && location=='$Location'] | [0].name" -o tsv
if ($LASTEXITCODE -ne 0) {
  throw "Could not check whether Azure OpenAI account '$openaiName' is soft-deleted."
}
if ($deletedOpenAI) {
  az cognitiveservices account purge `
    --name $openaiName `
    --resource-group $ResourceGroup `
    --location $Location --output none
  if ($LASTEXITCODE -ne 0) {
    throw "Could not purge soft-deleted Azure OpenAI account '$openaiName' in '$Location'."
  }
  Write-Host "      purged." -ForegroundColor Green
} else {
  Write-Host "      nothing to purge." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Teardown complete. All resources removed. ===" -ForegroundColor Green
Write-Host "Bring the demo back any time with:" -ForegroundColor Cyan
Write-Host "  ./scripts/demo-up.ps1 -ResourceGroup $ResourceGroup -Location $Location"
