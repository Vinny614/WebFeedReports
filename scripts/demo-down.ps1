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
#>
param(
  [string]$ResourceGroup = "rg-webscrape",
  [string]$ParamFile = "infra/main.bicepparam"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$paramPath = Join-Path $repoRoot $ParamFile

$paramText = Get-Content $paramPath -Raw
$namePrefix = ([regex]::Match($paramText, "param\s+namePrefix\s*=\s*'([^']+)'")).Groups[1].Value
$location = ([regex]::Match($paramText, "param\s+location\s*=\s*'([^']+)'")).Groups[1].Value
$openaiName = "$namePrefix-openai"

Write-Host "=== WebFeedReports demo: DOWN ===" -ForegroundColor Cyan
Write-Host "  Resource group : $ResourceGroup"
Write-Host "  OpenAI account : $openaiName ($location)"
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
try {
  az cognitiveservices account purge `
    --name $openaiName `
    --resource-group $ResourceGroup `
    --location $location --output none 2>$null
  Write-Host "      purged." -ForegroundColor Green
} catch {
  Write-Host "      nothing to purge (or already purged)." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "=== Teardown complete. All resources removed. ===" -ForegroundColor Green
Write-Host "Bring the demo back any time with:" -ForegroundColor Cyan
Write-Host "  ./scripts/demo-up.ps1 -ResourceGroup $ResourceGroup"
