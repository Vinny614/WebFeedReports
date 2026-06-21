using 'main.bicep'

// Short prefix for all resource names (keep lowercase, <= 11 chars recommended
// because it seeds storage/registry names which have strict limits).
param namePrefix = 'webscrape'

// Region for all resources. Ensure Azure OpenAI + the chosen model are available
// in this region (e.g. eastus, eastus2, swedencentral).
param location = 'centralus'

// On first deploy, push images to ACR then update these. A simple bootstrap is
// to deploy infra first with a public placeholder, build/push, then redeploy.
param apiImage = 'webscrapeacr.azurecr.io/webfeed-api:latest'
param workerImage = 'webscrapeacr.azurecr.io/webfeed-worker:latest'
param frontendImage = 'webscrapeacr.azurecr.io/webfeed-frontend:v2'
