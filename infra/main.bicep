// WebFeedReports — main deployment (resource group scope).
// Deploy into a pre-created resource group:
//   az deployment group create -g <rg> -f infra/main.bicep -p infra/main.bicepparam
//
// All Azure access uses Managed Identity (no keys). Images must exist in ACR
// before the container apps can start; on first deploy you may pass placeholder
// images, push real images, then redeploy or update the apps.

targetScope = 'resourceGroup'

@description('Short prefix used for resource names, e.g. "wfr-dev".')
param namePrefix string

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Container image references (registry/repo:tag). Set after ACR build.')
param apiImage string
param workerImage string
param frontendImage string

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module registry 'modules/registry.bicep' = {
  name: 'registry'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module openai 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module servicebus 'modules/servicebus.bicep' = {
  name: 'servicebus'
  params: {
    location: location
    namePrefix: namePrefix
  }
}

module caeEnv 'modules/containerapp-env.bicep' = {
  name: 'cae-env'
  params: {
    location: location
    namePrefix: namePrefix
    logAnalyticsCustomerId: monitoring.outputs.logAnalyticsCustomerId
    logAnalyticsId: monitoring.outputs.logAnalyticsId
  }
}

module rbac 'modules/rbac.bicep' = {
  name: 'rbac'
  params: {
    storageName: storage.outputs.storageName
    searchName: '${namePrefix}-search'
    openaiName: '${namePrefix}-openai'
    servicebusNamespaceName: servicebus.outputs.namespaceName
    registryName: registry.outputs.registryName
    apiPrincipalId: identity.outputs.apiPrincipalId
    workerPrincipalId: identity.outputs.workerPrincipalId
  }
}

module apps 'modules/containerapps.bicep' = {
  name: 'apps'
  dependsOn: [
    rbac
  ]
  params: {
    location: location
    namePrefix: namePrefix
    environmentId: caeEnv.outputs.environmentId
    registryLoginServer: registry.outputs.loginServer
    apiIdentityId: identity.outputs.apiIdentityId
    apiClientId: identity.outputs.apiClientId
    workerIdentityId: identity.outputs.workerIdentityId
    workerClientId: identity.outputs.workerClientId
    apiImage: apiImage
    workerImage: workerImage
    frontendImage: frontendImage
    blobEndpoint: storage.outputs.blobEndpoint
    tableEndpoint: storage.outputs.tableEndpoint
    searchEndpoint: search.outputs.searchEndpoint
    searchIndexName: 'webfeed-chunks'
    openaiEndpoint: openai.outputs.openaiEndpoint
    embedDeploymentName: openai.outputs.embedDeploymentName
    chatDeploymentName: openai.outputs.chatDeploymentName
    servicebusFqdn: servicebus.outputs.fqdn
    ingestQueueName: servicebus.outputs.ingestQueueName
    reportQueueName: servicebus.outputs.reportQueueName
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

output registryLoginServer string = registry.outputs.loginServer
output storageName string = storage.outputs.storageName
output apiFqdn string = apps.outputs.apiFqdn
output frontendFqdn string = apps.outputs.frontendFqdn
