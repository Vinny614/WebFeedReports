// Azure Container Registry. Pull access is granted to the app identities via
// AcrPull role assignments in rbac.bicep (no admin user / no keys).

param location string
param namePrefix string

resource registry 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: toLower(replace('${namePrefix}acr', '-', ''))
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false
  }
}

output registryId string = registry.id
output registryName string = registry.name
output loginServer string = registry.properties.loginServer
