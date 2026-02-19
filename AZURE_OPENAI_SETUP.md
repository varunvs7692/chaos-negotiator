# Azure OpenAI Setup Guide for Chaos Negotiator

## Overview
Chaos Negotiator now uses **Azure OpenAI Service** (GPT-4) instead of Anthropic Claude. This guide walks you through deploying and configuring Azure OpenAI for your project.

## Step 1: Create Azure OpenAI Service

### Via Azure Portal:
1. Go to **[Azure Portal](https://portal.azure.com)**
2. Click **+ Create a resource**
3. Search for **"Azure OpenAI"**
4. Click **Create**
5. Fill in the form:
   - **Subscription**: Your Azure subscription
   - **Resource Group**: `chaos-negotiator-rg` (create if needed)
   - **Region**: East US, France Central, or UK South (check [regional availability](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models))
   - **Name**: `chaos-negotiator-openai`
   - **Pricing Tier**: Standard S0

### Via Azure CLI:
```powershell
az cognitiveservices account create \
  --name chaos-negotiator-openai \
  --resource-group chaos-negotiator-rg \
  --kind OpenAI \
  --sku s0 \
  --location eastus \
  --custom-domain chaos-negotiator-openai
```

## Step 2: Deploy GPT-4 Model

### Via Azure Portal:
1. Navigate to your OpenAI resource
2. Click **"Open in Azure OpenAI Studio"**
3. Go to **Deployments** (left sidebar)
4. Click **"Create new deployment"**
5. Configure:
   - **Model name**: `gpt-4`
   - **Model version**: Latest stable (e.g., `0613`)
   - **Deployment name**: `gpt-4`
   - **Tokens per minute**: 40K (adjust based on usage)
6. Click **Create**

### Via Azure CLI:
```powershell
az cognitiveservices account deployment create \
  --name chaos-negotiator-openai \
  --resource-group chaos-negotiator-rg \
  --deployment-id gpt-4 \
  --model-name gpt-4 \
  --model-version 0613
```

## Step 3: Get Credentials

### Get API Key (Azure Portal):
1. In your OpenAI resource, click **Keys and Endpoint**
2. Copy one of the API keys

### Get API Key (Azure CLI):
```powershell
$key = az cognitiveservices account keys list `
  --name chaos-negotiator-openai `
  --resource-group chaos-negotiator-rg `
  --query "key1" -o tsv

Write-Host "AZURE_OPENAI_KEY=$key"
```

### Get Endpoint:
Your endpoint follows this format:
```
https://<resource-name>.openai.azure.com/
```

Replace `<resource-name>` with your resource name (e.g., `chaos-negotiator-openai`)

## Step 4: Configure Local Environment

### Set Environment Variables (PowerShell):
```powershell
$env:AZURE_OPENAI_KEY = "your-api-key-here"
$env:AZURE_OPENAI_ENDPOINT = "https://chaos-negotiator-openai.openai.azure.com/"
```

### Verify Configuration:
```powershell
Write-Host "AZURE_OPENAI_KEY: $env:AZURE_OPENAI_KEY"
Write-Host "AZURE_OPENAI_ENDPOINT: $env:AZURE_OPENAI_ENDPOINT"
```

## Step 5: Test the Agent

### Run Agent with Azure OpenAI:
```powershell
cd "c:\Users\76SAHU\OneDrive\Desktop\chaos-negotiator"
python -m chaos_negotiator.main
```

### Expected Output:
The agent should:
1. ✅ Connect to Azure OpenAI (no connection errors)
2. ✅ Analyze deployment risk
3. ✅ Generate deployment contract with guardrails from real GPT-4 responses
4. ✅ Save contract JSON file

## Step 6: Deploy to Azure Container Apps

Update your GitHub secrets:

1. Go to your GitHub repo: `varunvs7692/chaos-negotiator`
2. **Settings** → **Secrets and variables** → **Actions**
3. Add secrets:
   - **AZURE_OPENAI_KEY**: Your API key
   - **AZURE_OPENAI_ENDPOINT**: Your endpoint URL

## Troubleshooting

### Error: "Azure OpenAI credentials not configured"
**Solution**: Ensure both environment variables are set:
```powershell
$env:AZURE_OPENAI_KEY = "sk-..."
$env:AZURE_OPENAI_ENDPOINT = "https://xxx.openai.azure.com/"
```

### Error: "InvalidRequestError: Invalid deployment ID"
**Solution**: Verify deployment name matches in code:
- Check Azure OpenAI Studio → Deployments
- Update `self.model = "gpt-4"` in [agent.py](chaos_negotiator/agent/agent.py#L30) if deployment name differs

### Error: "Quota exceeded"
**Solution**: Check your quota:
```powershell
az cognitiveservices account list-usage \
  --name chaos-negotiator-openai \
  --resource-group chaos-negotiator-rg
```
Upgrade tokens per minute in Deployments tab.

### Slow Responses
**Solution**: This is normal for initial deployment. Azure OpenAI may have first-time latency. Wait 30 seconds or adjust timeout in code.

## Cost Estimation

| Component | Monthly Cost (Estimate) |
|-----------|------------------------|
| Azure OpenAI (GPT-4, 1M tokens) | ~$30 |
| Container Apps | ~$20 |
| App Insights | ~$5 |
| **Total** | **~$55** |

For hackathon: Most cloud providers offer free credits ($50-200).

## References

- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [GPT-4 Model Details](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/models#gpt-4-models)
- [Azure OpenAI Quickstart](https://learn.microsoft.com/en-us/azure/ai-services/openai/quickstart)

---

**Ready to run Chaos Negotiator with Azure OpenAI!** 🚀
