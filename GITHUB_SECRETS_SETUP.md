# GitHub Secrets Setup Guide

## Quick Setup Instructions

Go to: https://github.com/varunvs7692/chaos-negotiator/settings/secrets/actions

The deployment workflow now uses explicit fields for `azure/login` (not `AZURE_CREDENTIALS` JSON), so add these secrets:

## Required Azure Login Secrets

### 1. `AZURE_CLIENT_ID`
Service principal application (client) ID.

### 2. `AZURE_TENANT_ID`
Microsoft Entra tenant ID.

### 3. `AZURE_SUBSCRIPTION_ID`
Azure subscription ID used for deployments.

### 4. `AZURE_CLIENT_SECRET`
Service principal client secret.

## Required Container Registry Secrets

### 5. `AZURE_REGISTRY_URL`
Example: `yourregistry.azurecr.io`

### 6. `AZURE_REGISTRY_USERNAME`
ACR admin username.

### 7. `AZURE_REGISTRY_PASSWORD`
ACR admin password.

## Optional App Secrets

### 8. `AZURE_OPENAI_KEY`
Azure OpenAI API key.

### 9. `AZURE_OPENAI_ENDPOINT`
Azure OpenAI endpoint URL.

## Verification Checklist

After adding secrets, verify you have:
- [ ] AZURE_CLIENT_ID
- [ ] AZURE_TENANT_ID
- [ ] AZURE_SUBSCRIPTION_ID
- [ ] AZURE_CLIENT_SECRET
- [ ] AZURE_REGISTRY_URL
- [ ] AZURE_REGISTRY_USERNAME
- [ ] AZURE_REGISTRY_PASSWORD

## If You Previously Used `AZURE_CREDENTIALS`

You can keep it for reference, but the workflow no longer depends on it for login.

## Security Note

If credentials were shared in chat or committed anywhere, rotate them immediately:
1. Regenerate service principal secret.
2. Regenerate ACR password (or disable admin user and switch to federated/OIDC auth later).
3. Update GitHub secrets with new values.

## Test the Workflow

After updating secrets, rerun from: https://github.com/varunvs7692/chaos-negotiator/actions
