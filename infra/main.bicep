targetScope = 'resourceGroup'

@minLength(1)
@maxLength(64)
@description('Name of the azd environment, used for tags and the project name.')
param environmentName string = 'prel42'

@minLength(1)
@description('Primary Azure region. It must support Foundry hosted agents and the selected models.')
param location string = resourceGroup().location

@description('Object ID of the user who runs the notebooks and agents.')
param principalId string

@description('Principal type of principalId.')
param principalType string = 'User'

@description('Optional object ID of a service principal that runs the setup scripts (for example, the Skillable lab service principal).')
param setupServicePrincipalId string = ''

@description('Optional suffix for Foundry resource names, so a re-created lab never collides with a soft-deleted account.')
param foundryNameSuffix string = ''

@description('Model deployments serialized by the azure.ai.agents azd extension.')
param aiProjectDeploymentsJson string = '[]'

@description('Enable Application Insights and Log Analytics.')
param enableMonitoring bool = true

@description('Azure AI Search SKU.')
@allowed([
  'basic'
  'standard'
  'standard2'
  'standard3'
  'storage_optimized_l1'
  'storage_optimized_l2'
  'serverless'
])
param searchServiceSku string = 'serverless'

@description('Azure AI Search region. Serverless Search is only available in some regions.')
param searchServiceLocation string = 'northcentralus'

@description('Create a Microsoft Fabric capacity for the Fabric IQ notebooks and agent.')
param enableFabricCapacity bool = false

@description('Microsoft Fabric capacity SKU.')
param fabricSkuName string = 'F2'

@description('Optional user UPN to add as a Fabric capacity administrator.')
param fabricAdminUpn string = ''

@description('Optional service-principal object ID to add as a Fabric capacity administrator. Defaults to setupServicePrincipalId.')
param fabricServicePrincipalId string = ''

var configuredDeployments = json(aiProjectDeploymentsJson)
var fallbackDeployments = [
  {
    name: 'gpt-5.4'
    model: {
      format: 'OpenAI'
      name: 'gpt-5.4'
      version: '2026-03-05'
    }
    sku: {
      name: 'GlobalStandard'
      capacity: 50
    }
  }
  {
    name: 'text-embedding-3-large'
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: '1'
    }
    sku: {
      name: 'GlobalStandard'
      capacity: 30
    }
  }
]
var deployments = empty(configuredDeployments) ? fallbackDeployments : configuredDeployments
var chatDeployments = filter(deployments, deployment => deployment.model.name != 'text-embedding-3-large')
var embeddingDeployments = filter(deployments, deployment => deployment.model.name == 'text-embedding-3-large')
var tags = {
  'azd-env-name': environmentName
}

module aiProject 'core/ai/ai-project.bicep' = {
  name: 'ai-project'
  params: {
    tags: tags
    location: location
    aiFoundryProjectName: 'ai-project-${environmentName}'
    foundryNameSuffix: foundryNameSuffix
    principalId: principalId
    principalType: principalType
    setupServicePrincipalId: setupServicePrincipalId
    deployments: deployments
    enableMonitoring: enableMonitoring
    searchServiceSku: searchServiceSku
    searchServiceLocation: searchServiceLocation
  }
}

module fabricCapacity 'core/fabric/fabric-capacity.bicep' = if (enableFabricCapacity) {
  name: 'fabric-capacity'
  params: {
    name: 'fabric${uniqueString(subscription().id, resourceGroup().id)}'
    location: location
    skuName: fabricSkuName
    adminMember: empty(fabricAdminUpn) ? principalId : fabricAdminUpn
    servicePrincipalId: empty(fabricServicePrincipalId) ? setupServicePrincipalId : fabricServicePrincipalId
    tags: tags
  }
}

module webIq 'core/webiq/webiq.bicep' = {
  name: 'webiq'
  params: {
    name: 'webiq-${uniqueString(subscription().id, resourceGroup().id)}'
    tags: tags
  }
}

output AZURE_RESOURCE_GROUP string = resourceGroup().name
output AZURE_LOCATION string = location
output AZURE_AI_ACCOUNT_ID string = aiProject.outputs.accountId
output AZURE_AI_PROJECT_ID string = aiProject.outputs.projectId
output AZURE_AI_FOUNDRY_PROJECT_ID string = aiProject.outputs.projectId
output AZURE_AI_ACCOUNT_NAME string = aiProject.outputs.aiServicesAccountName
output AZURE_AI_PROJECT_NAME string = aiProject.outputs.projectName
output AZURE_AI_PROJECT_ENDPOINT string = aiProject.outputs.AZURE_AI_PROJECT_ENDPOINT
output FOUNDRY_PROJECT_ENDPOINT string = aiProject.outputs.AZURE_AI_PROJECT_ENDPOINT
output MICROSOFT_FOUNDRY_PROJECT_ENDPOINT string = aiProject.outputs.AZURE_AI_PROJECT_ENDPOINT
output MICROSOFT_FOUNDRY_PROJECT_ID string = aiProject.outputs.projectId

output AZURE_AI_MODEL_DEPLOYMENT_NAME string = string(chatDeployments[0].name)
output AZURE_OPENAI_CHATGPT_DEPLOYMENT string = string(chatDeployments[0].name)
output AZURE_OPENAI_CHATGPT_MODEL_NAME string = string(chatDeployments[0].model.name)
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = string(embeddingDeployments[0].name)
output AZURE_OPENAI_ENDPOINT string = aiProject.outputs.AZURE_OPENAI_ENDPOINT
output AZURE_OPENAI_SERVICE_NAME string = aiProject.outputs.aiServicesAccountName

output AZURE_AI_SEARCH_SERVICE_NAME string = aiProject.outputs.search.serviceName
output AZURE_AI_SEARCH_SERVICE_ENDPOINT string = aiProject.outputs.search.serviceEndpoint
output AZURE_SEARCH_SERVICE_NAME string = aiProject.outputs.search.serviceName
output AZURE_SEARCH_SERVICE_ENDPOINT string = aiProject.outputs.search.serviceEndpoint
@description('Azure AI Search system-assigned managed identity principal ID (federated credential subject for Work IQ)')
output SEARCH_SERVICE_PRINCIPAL_ID string = aiProject.outputs.search.principalId

output AZURE_STORAGE_CONNECTION_NAME string = aiProject.outputs.storage.connectionName
output AZURE_STORAGE_ACCOUNT_NAME string = aiProject.outputs.storage.accountName
output APPLICATIONINSIGHTS_CONNECTION_STRING string = aiProject.outputs.APPLICATIONINSIGHTS_CONNECTION_STRING
output APPLICATIONINSIGHTS_RESOURCE_ID string = aiProject.outputs.APPLICATIONINSIGHTS_RESOURCE_ID

output FABRIC_CAPACITY_NAME string = enableFabricCapacity ? fabricCapacity!.outputs.name : ''
output FABRIC_CAPACITY_ID string = enableFabricCapacity ? fabricCapacity!.outputs.id : ''
output FABRIC_TENANT_ID string = enableFabricCapacity ? tenant().tenantId : ''
output AZURE_TENANT_ID string = tenant().tenantId
