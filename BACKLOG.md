# WebFeedReports — Backlog

Forward-looking enhancements. Nothing here is implemented yet; captured for planning.
Recently shipped (for context): hybrid **search reranker** (semantic L2 + score threshold)
and the grounded **Chat** page (streaming RAG over the AI Search index).

---

## 1. Foundry-based chat agent with web search

**Goal:** Let the Chat page answer from the live web in addition to the indexed
corpus, while staying inside Azure and keyless in our own code.

**Approach:** Azure AI Foundry **Agent Service** with two tools:
- **Grounding with Bing Search** (live web + citations).
- **Azure AI Search** tool pointed at the existing index.

The `api` Container App calls the agent with its managed identity; Foundry holds the
Bing connection server-side (no secret in our code).

**Touchpoints:**
- Infra: Foundry account + project, model deployment, Grounding-with-Bing resource +
  connection, RBAC to the `api` managed identity (e.g. Azure AI User on the project).
- Code: refactor `stream_chat` in `packages/domain/webfeed_domain/chat.py` to drive a
  Foundry thread/run and map agent events onto the existing SSE frames.
- Config/deps: project endpoint + agent id in `webfeed_platform/config.py`;
  add `azure-ai-projects` / `azure-ai-agents` to `apps/api/requirements.txt`.

**Decisions to lock:** deploy region availability (Agents + Bing grounding), per-query
Bing cost, acceptance that the Bing tool queries the public web.

**Effort:** Moderate (bulk is infra; SDK swap on the chat path only).

---

## 2. Knowledge graph of the ingested data

**Goal:** Turn ingested content (RSS, web, APIs) into an entity–relationship graph.

**Approach:** Extract `(entity, relationship, entity)` triples + entity types per chunk
using Azure OpenAI structured outputs (optionally Azure AI Language NER), then load into
a graph store. Recommended store: **Azure Cosmos DB for Apache Gremlin** (managed,
Entra/MI RBAC, traversal-native). Alternative: PostgreSQL Flexible Server + Apache AGE.

**Touchpoints:**
- Domain: new `webfeed_domain/graph.py` for extraction + upsert.
- Worker: new handler after `index_chunks` in `apps/worker/app/handlers.py`.
- Infra: Cosmos DB (Gremlin) module + RBAC (worker write, api read).

**Decisions to lock:** graph **schema** (entity/relationship types that matter for
briefings) and an **entity-resolution / dedup** strategy (canonicalize aliases) — this
is where most of the real effort is, not the plumbing.

**Effort:** Moderate–high.

---

## 3. Visualize & interrogate the graph

**Goal:** In-product exploration of the graph — click through entities, see connections,
ask questions.

**Approach:**
- **Visualize:** new `frontend/app/graph/page.tsx` rendering a node-link diagram with
  **Cytoscape.js** or **react-force-graph**. (Secondary analyst view could use Azure
  Managed Grafana Node Graph or Power BI.)
- **Interrogate (structured):** new `/graph` API routes — `neighbors`, `path`,
  `subgraph` (filter by type/tag/source/date) returning `{nodes, edges}`.
- **Interrogate (natural language):** `/graph/ask` that translates a question to a
  Gremlin query via Azure OpenAI and returns a subgraph + narrative; optionally expose
  the graph as a **tool** to the chat agent so answers can highlight a subgraph.

**Depends on:** item 2 (graph store populated).

**Effort:** Moderate–high (store + API + graph page; NL-to-query adds polish).

---

## 4. (Optional) GraphRAG for thematic Q&A

**Goal:** Answer cross-corpus, "global" questions ("major themes this month",
"how are these events connected") that plain vector RAG can't.

**Approach:** Microsoft **GraphRAG** via the Azure Solution Accelerator — builds an
entity graph + community summaries on the services we already run (Azure AI Search +
Blob + Azure OpenAI). Its extracted graph can also feed the item-3 visualization.

**Effort:** Moderate; complements items 2–3 rather than replacing them.

---

## 5. (Optional) Foundry IQ knowledge base

**Goal:** Unified, agentic retrieval across multiple knowledge sources (index + web +
files) with built-in query planning and reranking.

**When:** Consider once sources fan out beyond the single AI Search index, or when the
briefing flow becomes an agent that needs grounded retrieval as a tool. Would replace
some hand-rolled retrieval glue in `query.py` / `reporting.py`.
