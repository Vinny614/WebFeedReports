<#
.SYNOPSIS
  Deploy WebFeedReports infrastructure into an existing resource group.

.EXAMPLE
  ./scripts/deploy.ps1 -ResourceGroup wfr-rg
#>
param(
  [Parameter(Mandatory = $true)][string]$ResourceGroup,
  [string]$ParamFile = "infra/main.bicepparam"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Host "Deploying infrastructure to resource group '$ResourceGroup'..."
az deployment group create `
  --resource-group $ResourceGroup `
  --template-file "$repoRoot/infra/main.bicep" `
  --parameters "$repoRoot/$ParamFile"

Write-Host "Deployment complete. Next:"
Write-Host "  1. Run scripts/build-and-push.ps1 to build images + publish sources.yaml."
Write-Host "  2. Update image params in $ParamFile to the ACR image refs."
Write-Host "  3. Re-run this script to roll images onto the apps."
