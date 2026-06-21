# Deployment Plan: WebFeedReports

Status: In Progress

## 1. Overview

Cloud-native briefing platform on Azure Container Apps that ingests RSS feeds and
web pages, stores raw content in Blob Storage, indexes processed chunks (with vector
embeddings) into Azure AI Search, and generates structured briefing reports with
Azure OpenAI. Authentication uses Managed Identity only (DefaultAzureCredential).
No API keys. No secrets.

- Deployment mode: MODIFY (greenfield repo, infra added under `infra/`).
- IaC: Bicep.
- Source list delivery: Option B (publish `config/sources.yaml` to Blob Storage at deploy
  time; worker reads it at runtime via managed identity).

## 2. Target Azure Context

- Subscription: <to be confirmed at deploy time>
- Resource Group: <user-created, name to be supplied>  # user will create this
- Region: <to be confirmed at deploy time>
- Naming convention: `<prefix>-webfeed-<resource>-<env>`

> The resource group is created by the user ahead of deployment. The Bicep
> deployment targets this existing resource group (resourceGroup scope).

## 3. Services (Initial: 3 Container Apps)

| Service   | Type            | Responsibility                                        |
|-----------|-----------------|-------------------------------------------------------|
| frontend  | Container App   | Demo UI: dashboard, search, report request, status    |
| api       | Container App   | FastAPI orchestration: sources, query, reports, jobs  |
| worker    | Container App   | Ingestion, extraction, indexing, report generation    |

## 4. Azure Resources to Provision (Bicep)

| Resource                          | Purpose                                         |
|-----------------------------------|-------------------------------------------------|
| Container Apps Environment        | Shared environment for all three apps           |
| Container App: frontend           | User interface                                  |
| Container App: api                | FastAPI API service                             |
| Container App: worker             | Background processing                           |
| Azure Container Registry (ACR)    | Container images                                |
| User-Assigned Managed Identity x2 | Identity for api and worker                     |
| Azure Storage Account             | Blob (raw + reports + sources.yaml), Tables     |
| Azure AI Search                   | Indexed chunks + vector fields                  |
| Azure OpenAI                      | Embeddings + report generation                  |
| Azure Service Bus                 | Ingestion + report job queues                   |
| Log Analytics Workspace           | Logs                                            |
| Application Insights              | Traces / telemetry                              |

## 5. Source List Delivery (Option B)

- File: `config/sources.yaml` (versioned in repo).
- Deploy step publishes `config/sources.yaml` to Blob container `sources`.
- Worker reads the blob at startup / on a sync job using managed identity.
- Worker seeds the source registry (Table Storage) from the file.
- Registry is runtime source of truth; API/frontend can add/disable sources later.
- Bicep passes only a pointer (container + blob name) as env vars:
  - `SOURCES_CONTAINER` + `SOURCES_BLOB_NAME`
- Bicep never contains the feed list itself.

## 6. Managed Identity & RBAC

All Azure access uses DefaultAzureCredential. No keys.

| Identity         | Target            | Role                                      |
|------------------|-------------------|-------------------------------------------|
| api-identity     | Service Bus       | Azure Service Bus Data Sender             |
| api-identity     | Storage (Table)   | Storage Table Data Contributor            |
| api-identity     | AI Search         | Search Index Data Reader                  |
| api-identity     | Storage (Blob)    | Storage Blob Data Reader (reports)        |
| worker-identity  | Storage (Blob)    | Storage Blob Data Contributor             |
| worker-identity  | Storage (Table)   | Storage Table Data Contributor            |
| worker-identity  | Service Bus       | Azure Service Bus Data Receiver + Sender  |
| worker-identity  | AI Search         | Search Index Data Contributor             |
| worker-identity  | Azure OpenAI      | Cognitive Services OpenAI User            |
| api + worker     | ACR               | AcrPull                                   |

Local dev: same DefaultAzureCredential resolves via developer Entra sign-in.

## 7. Configuration (Container App env vars, no secrets)

| Variable                       | Service       | Notes                              |
|--------------------------------|---------------|------------------------------------|
| AZURE_CLIENT_ID                | api, worker   | User-assigned MI client id         |
| STORAGE_ACCOUNT_BLOB_URL       | api, worker   | Blob endpoint                      |
| STORAGE_ACCOUNT_TABLE_URL      | api, worker   | Table endpoint                     |
| SEARCH_ENDPOINT                | api, worker   | AI Search endpoint                 |
| OPENAI_ENDPOINT                | worker        | Azure OpenAI endpoint              |
| OPENAI_EMBED_DEPLOYMENT        | worker        | Embedding deployment name          |
| OPENAI_CHAT_DEPLOYMENT         | worker        | Report generation deployment name  |
| SERVICEBUS_FQDN                | api, worker   | Fully qualified namespace          |
| SERVICEBUS_INGEST_QUEUE        | api, worker   | Ingestion queue name               |
| SERVICEBUS_REPORT_QUEUE        | api, worker   | Report queue name                  |
| SOURCES_CONTAINER              | worker        | Blob container for sources.yaml    |
| SOURCES_BLOB_NAME              | worker        | sources.yaml                       |
| APPLICATIONINSIGHTS_CONNECTION_STRING | all    | Telemetry                          |
| API_BASE_URL                   | frontend      | API endpoint                       |

## 8. Bicep Module Layout

```
infra/
  main.bicep                      # rg-scope entry, wires modules + role assignments
  main.bicepparam                 # parameter values
  modules/
    identity.bicep                # user-assigned identities
    monitoring.bicep              # log analytics + app insights
    registry.bicep                # ACR
    storage.bicep                 # account, blob containers, tables
    search.bicep                  # AI Search
    openai.bicep                  # Azure OpenAI + deployments
    servicebus.bicep              # namespace + queues
    containerapp-env.bicep        # Container Apps environment
    containerapps.bicep           # the 3 container apps
    rbac.bicep                    # role assignments
```

## 9. Build / Deploy Reference

1. Build and push images to ACR for frontend, api, worker.
2. Deploy Bicep to the existing resource group (resourceGroup scope).
3. Publish `config/sources.yaml` to the `sources` blob container.
4. Worker seeds source registry from blob on startup / sync.
5. Validate health endpoints and end-to-end flow.

```
az deployment group create -g <rg> -f infra/main.bicep -p infra/main.bicepparam
az storage blob upload --account-name <sa> --auth-mode login \
  -c sources -n sources.yaml -f config/sources.yaml
```

## 10. Implementation Phases

1. Foundation: monorepo structure, shared packages, config model.
2. Platform + identity: Bicep for all resources, MI + RBAC wired.
3. Frontend shell + API contracts.
4. Ingestion pipeline + raw blob persistence + sources.yaml seeding.
5. Extraction + indexing into AI Search.
6. Query experience.
7. Report generation workflow (async jobs).
8. Hardening + observability.
9. Optional service decomposition.

## 11. Key Decisions

- Bicep (Azure-native stack).
- 3 services on Container Apps; modular monorepo first.
- Option B source delivery: sources.yaml -> Blob -> registry.
- Managed Identity only; no keys/secrets.
- Async report jobs via Service Bus.
- Blob = raw store; AI Search = retrieval; Table = job/source state.

## 12. Open Items / Defaults Applied

- Metadata store: Table Storage (default applied).
- Identity model: user-assigned managed identities (default applied).
- Subscription, resource group name, region: to be supplied at deploy time via params.
