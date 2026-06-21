// The three Container Apps: frontend, api, worker.
// Images are pulled from ACR using the app's user-assigned managed identity.

param location string
param namePrefix string
param environmentId string

param registryLoginServer string

param apiIdentityId string
param apiClientId string
param workerIdentityId string
param workerClientId string

param apiImage string
param workerImage string
param frontendImage string

param blobEndpoint string
param tableEndpoint string
param searchEndpoint string
param searchIndexName string
param openaiEndpoint string
param embedDeploymentName string
param chatDeploymentName string
param servicebusFqdn string
param ingestQueueName string
param reportQueueName string
param appInsightsConnectionString string

var commonAzureEnv = [
  { name: 'STORAGE_ACCOUNT_BLOB_URL', value: blobEndpoint }
  { name: 'STORAGE_ACCOUNT_TABLE_URL', value: tableEndpoint }
  { name: 'SEARCH_ENDPOINT', value: searchEndpoint }
  { name: 'SEARCH_INDEX_NAME', value: searchIndexName }
  { name: 'SERVICEBUS_FQDN', value: servicebusFqdn }
  { name: 'SERVICEBUS_INGEST_QUEUE', value: ingestQueueName }
  { name: 'SERVICEBUS_REPORT_QUEUE', value: reportQueueName }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
]

// ---------------- API ----------------
resource api 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: registryLoginServer
          identity: apiIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(commonAzureEnv, [
            { name: 'AZURE_CLIENT_ID', value: apiClientId }
            { name: 'OPENAI_ENDPOINT', value: openaiEndpoint }
            { name: 'OPENAI_EMBED_DEPLOYMENT', value: embedDeploymentName }
          ])
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// ---------------- Worker ----------------
resource worker 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-worker'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${workerIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      registries: [
        {
          server: registryLoginServer
          identity: workerIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'worker'
          image: workerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(commonAzureEnv, [
            { name: 'AZURE_CLIENT_ID', value: workerClientId }
            { name: 'OPENAI_ENDPOINT', value: openaiEndpoint }
            { name: 'OPENAI_EMBED_DEPLOYMENT', value: embedDeploymentName }
            { name: 'OPENAI_CHAT_DEPLOYMENT', value: chatDeploymentName }
            { name: 'SOURCES_CONTAINER', value: 'sources' }
            { name: 'SOURCES_BLOB_NAME', value: 'sources.yaml' }
          ])
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

// ---------------- Frontend ----------------
resource frontend 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${apiIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 3000
        transport: 'auto'
      }
      registries: [
        {
          server: registryLoginServer
          identity: apiIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'API_BASE_URL', value: 'https://${api.properties.configuration.ingress.fqdn}' }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
    }
  }
}

output apiFqdn string = api.properties.configuration.ingress.fqdn
output frontendFqdn string = frontend.properties.configuration.ingress.fqdn
