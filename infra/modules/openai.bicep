// Azure OpenAI account with embedding + chat deployments.
// Key auth is disabled; access is via Entra ID (Cognitive Services OpenAI User).

param location string
param namePrefix string
param embedDeploymentName string = 'text-embedding-3-large'
param chatDeploymentName string = 'gpt-4o'

@description('Deployment SKU. GlobalStandard has the broadest regional availability.')
param deploymentSku string = 'GlobalStandard'

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: '${namePrefix}-openai'
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: toLower(replace('${namePrefix}-openai', '_', '-'))
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource embedDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: embedDeploymentName
  sku: {
    name: deploymentSku
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openai
  name: chatDeploymentName
  dependsOn: [
    embedDeployment
  ]
  sku: {
    name: deploymentSku
    capacity: 20
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

output openaiId string = openai.id
output openaiEndpoint string = openai.properties.endpoint
output embedDeploymentName string = embedDeployment.name
output chatDeploymentName string = chatDeployment.name
