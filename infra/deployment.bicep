param location string = 'eastus'
param environment string = 'dev'
param appName string = 'chaos-negotiator'

module infrastructure 'main.bicep' = {
  name: 'infrastructure'
  params: {
    location: location
    environment: environment
    appName: appName
  }
}

output containerAppUrl string = infrastructure.outputs.containerAppUrl
output containerRegistry string = infrastructure.outputs.containerRegistryLoginServer
output appInsights string = infrastructure.outputs.appInsightsKey
