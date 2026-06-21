// Azure AI Search. Local (key) auth is disabled; RBAC is the only auth path.

param location string
param namePrefix string

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: '${namePrefix}-search'
  location: location
  sku: {
    name: 'basic'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    disableLocalAuth: true
    authOptions: null
  }
}

output searchId string = search.id
output searchEndpoint string = 'https://${search.name}.search.windows.net'
