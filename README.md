# WebFeedReports

Cloud-native briefing platform on **Azure Container Apps**. It ingests RSS feeds
and web pages, stores raw content in Blob Storage, indexes processed chunks (with
vector embeddings) into Azure AI Search, and generates structured briefing reports
with Azure OpenAI.

- **Auth:** Managed Identity only (`DefaultAzureCredential`). No API keys, no secrets.
- **Compute:** Three Container Apps — `frontend`, `api`, `worker`.
- **IaC:** Bicep (`infra/`).
- **Sources:** declarative `config/sources.yaml`, published to Blob and seeded into
  a Table Storage registry at runtime (Option B).

## Architecture

```
Browser → frontend (Next.js) → api (FastAPI) → Service Bus → worker
                                     |                          |
                                     v                          v
                              Azure AI Search           Blob + AI Search + Azure OpenAI
```

| Service  | Role                                                            |
|----------|-----------------------------------------------------------------|
| frontend | Demo UI: dashboard, search, report requests                     |
| api      | FastAPI orchestration: query, report submission, job status     |
| worker   | Scheduled + queued ingestion, extraction, indexing, reporting   |

## Repository layout

```
apps/
  frontend/        Next.js UI
  api/             FastAPI orchestration service
  worker/          Background ingestion/processing/reporting
packages/
  shared/          Pydantic models + job contracts
  platform/        config, identity (DefaultAzureCredential), clients, telemetry
  domain/          sources, ingestion, extraction, indexing, query, reporting, jobs
infra/             Bicep modules + main.bicep + main.bicepparam
config/sources.yaml  Declarative source list (published to Blob at deploy time)
scripts/           deploy.ps1, build-and-push.ps1
```

## Local development

```powershell
# Python (API/worker share the same packages)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e packages/shared -e packages/platform -e packages/domain
pip install -r apps/api/requirements.txt

cp .env.example .env   # fill in endpoints; auth uses your Entra (az login) sign-in
uvicorn app.main:app --app-dir apps/api --reload

# Frontend
cd apps/frontend; npm install; npm run dev
```

`DefaultAzureCredential` resolves locally via `az login` / VS Code sign-in, so no
keys are needed in development.

## Deploy

```powershell
# 1. Create the resource group (you own this step)
az group create -n wfr-rg -l eastus

# 2. Provision infrastructure
./scripts/deploy.ps1 -ResourceGroup wfr-rg

# 3. Build images + publish sources.yaml (Option B)
./scripts/build-and-push.ps1 -ResourceGroup wfr-rg -Registry <acrName> -StorageAccount <stName>

# 4. Update image params in infra/main.bicepparam, then redeploy
./scripts/deploy.ps1 -ResourceGroup wfr-rg
```

See [.azure/deployment-plan.md](.azure/deployment-plan.md) for the full plan,
RBAC matrix, and configuration contract.
