// Central RBAC: grants data-plane roles to the api and worker managed identities.
// No keys are used; these assignments are the only access path to each service.

param storageName string
param searchName string
param openaiName string
param servicebusNamespaceName string
param registryName string

param apiPrincipalId string
param workerPrincipalId string

// Built-in role definition IDs.
var roleStorageBlobContributor = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var roleStorageBlobReader = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
var roleStorageTableContributor = '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
var roleSearchIndexContributor = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var roleSearchIndexReader = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var roleSearchServiceContributor = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var roleServiceBusSender = '69a216fc-b8fb-44d8-bc22-1f3c2cd27a39'
var roleServiceBusReceiver = '4f6d3b9b-027b-4f4c-9142-0e5a2a2247e0'
var roleOpenAIUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
var roleAcrPull = '7f951dda-4ed3-4680-a7ca-43fe172d538d'

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}
resource search 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: searchName
}
resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: openaiName
}
resource servicebus 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' existing = {
  name: servicebusNamespaceName
}
resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' existing = {
  name: registryName
}

// ---------- Worker identity ----------
resource workerBlob 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, workerPrincipalId, roleStorageBlobContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobContributor)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, workerPrincipalId, roleStorageTableContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageTableContributor)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerSearch 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, workerPrincipalId, roleSearchIndexContributor)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleSearchIndexContributor)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Control-plane role so the worker can create/manage the search index.
resource workerSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, workerPrincipalId, roleSearchServiceContributor)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleSearchServiceContributor)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, workerPrincipalId, roleOpenAIUser)
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleOpenAIUser)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerSbSend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(servicebus.id, workerPrincipalId, roleServiceBusSender)
  scope: servicebus
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleServiceBusSender)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerSbReceive 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(servicebus.id, workerPrincipalId, roleServiceBusReceiver)
  scope: servicebus
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleServiceBusReceiver)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource workerAcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, workerPrincipalId, roleAcrPull)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAcrPull)
    principalId: workerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ---------- API identity ----------
resource apiBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, apiPrincipalId, roleStorageBlobReader)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageBlobReader)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource apiTable 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, apiPrincipalId, roleStorageTableContributor)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleStorageTableContributor)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource apiSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, apiPrincipalId, roleSearchIndexReader)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleSearchIndexReader)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource apiOpenAI 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, apiPrincipalId, roleOpenAIUser)
  scope: openai
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleOpenAIUser)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource apiSbSend 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(servicebus.id, apiPrincipalId, roleServiceBusSender)
  scope: servicebus
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleServiceBusSender)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource apiAcr 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, apiPrincipalId, roleAcrPull)
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleAcrPull)
    principalId: apiPrincipalId
    principalType: 'ServicePrincipal'
  }
}
