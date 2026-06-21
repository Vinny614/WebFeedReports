// Service Bus namespace with ingest + report queues. Local auth disabled.

param location string
param namePrefix string

resource namespace 'Microsoft.ServiceBus/namespaces@2022-10-01-preview' = {
  name: '${namePrefix}-bus'
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    disableLocalAuth: true
  }
}

resource ingestQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: namespace
  name: 'ingest-jobs'
  properties: {
    maxDeliveryCount: 5
    deadLetteringOnMessageExpiration: true
    lockDuration: 'PT5M'
  }
}

resource reportQueue 'Microsoft.ServiceBus/namespaces/queues@2022-10-01-preview' = {
  parent: namespace
  name: 'report-jobs'
  properties: {
    maxDeliveryCount: 5
    deadLetteringOnMessageExpiration: true
    lockDuration: 'PT5M'
  }
}

output namespaceId string = namespace.id
output namespaceName string = namespace.name
output fqdn string = '${namespace.name}.servicebus.windows.net'
output ingestQueueName string = ingestQueue.name
output reportQueueName string = reportQueue.name
