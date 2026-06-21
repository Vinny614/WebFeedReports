// User-assigned managed identities for the api and worker services.
// No keys are used anywhere; these identities are granted data-plane roles
// against Storage, Search, Service Bus and Azure OpenAI in rbac.bicep.

param location string
param namePrefix string

resource apiIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-api-id'
  location: location
}

resource workerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${namePrefix}-worker-id'
  location: location
}

output apiIdentityId string = apiIdentity.id
output apiClientId string = apiIdentity.properties.clientId
output apiPrincipalId string = apiIdentity.properties.principalId

output workerIdentityId string = workerIdentity.id
output workerClientId string = workerIdentity.properties.clientId
output workerPrincipalId string = workerIdentity.properties.principalId
