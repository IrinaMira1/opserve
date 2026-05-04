# OPServe — Development Documentation

An operational intelligence platform for semiconductor and hardware teams. Detects execution risk across projects by analyzing fragmented operational context.

## Core Concept

OPServe is not an orchestration system. It is a **fixed sequential pipeline** that always runs the same five agents in the same order:

```
Raw Data → Context → Structure → Risk → Impact → Role Actions
  (CC)      (WM)       (RA)     (IA)    (RT)
```

Each agent genuinely needs the previous agent's output. Parallelism lives **within** the Context Collector (fetching multiple data sources simultaneously), not between agents.

## Architecture

### Five Agents (Sequential)

1. **ContextCollectorAgent** — Reads all sources, extracts tasks/decisions/blockers
2. **WorkflowMapperAgent** — Maps project structure, ownership, dependencies
3. **RiskAgent** — Detects risks with evidence and severity
4. **ImpactAnalyzerAgent** — Estimates business impact, prioritizes
5. **RoleTranslatorAgent** — Generates role-specific checklists + perspective review

### Company Memory (Not an Agent)

Shared context layer storing operational history by project:
- `decisions.json` — past decisions
- `risks.json` — historical risks
- `action_items.json` — open/closed action items
- `blockers.json` — recurring blockers
- `feedback.json` — user feedback on recommendations
- `project_history.json` — project snapshots

Agents read from memory at the start of `_process()`. Agents return `memory_updates` in their output. `team.py` writes those updates after each agent completes.

### Connector System (Open Architecture)

Any data source implements `BaseConnector`:

```python
async def fetch(self, project_id: str, since: datetime | None) -> dict:
    # Returns structured data
    return {
        "tasks": [...],
        "events": [...],
        "messages": [...],
        "notes": [...],
        "documents": [...],
        "errors": [...]
    }
```

MVP ships with `MockDataConnector` (Project Atlas demo). Stubs for Trello, Google Calendar, Gmail, Sheets, meeting notes.

Context Collector calls all configured connectors in parallel with `asyncio.gather()`.

### Dual Trigger Modes

**Manual:**
```python
await run_analysis(["Project Atlas", "Project Beta"])
```

**Automatic:**
```python
await start_auto_poller(interval_seconds=900)  # 15 min
```

Poller detects new events since last scan, triggers analysis if changed. Runs as FastAPI background task via lifespan context manager.

## Running the System

### Locally

```bash
# CLI demo
python opserve_agents/main.py

# API server
uvicorn opserve_agents.api_server:app --reload

# Test endpoint
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"project_ids": ["Project Atlas"], "use_mock": true}'
```

### On Railway

1. Create new Railway project
2. Connect GitHub repo
3. Set `ANTHROPIC_API_KEY` environment variable
4. Deploy `Procfile`: `web: uvicorn opserve_agents.api_server:app --host 0.0.0.0 --port $PORT`

## Data Flow

```
POST /api/analyze {project_ids: ["Project Atlas"], use_mock: true}
    ↓
team.py: run_analysis()
    ↓
[Context Collector]
  - Fetches from all sources in parallel (asyncio.gather)
  - Returns: tasks, decisions, action items, blockers, missing context
  - Reads Company Memory for historical context
    ↓
[Workflow Mapper]
  - Maps: owners, dependencies, handoffs, unclear ownership
  - Reads Company Memory
    ↓
[Risk Agent]
  - Detects risks: Low/Medium/High/Critical
  - Evidence-backed, timeline impact, escalation flags
  - Reads historical risks from Company Memory
    ↓
[Impact Analyzer]
  - Business impact, delivery impact, executive decisions
  - Prioritized risk list
  - Reads decision history from Company Memory
    ↓
[Role Translator]
  - Role-specific outputs (exec / ops / engineering / supplier)
  - Each role gets: summary, checklist, decision needed, owner, deadline
  - Runs internal perspective review: validates recommendations
  - Reads feedback history from Company Memory
    ↓
Return final output JSON with all dashboard sections
```

## Project Memory Structure

Each project has its own memory directory at `~/.opserve/memory/<project_id>/`.

**Example: Project Atlas**
```
~/.opserve/memory/Project Atlas/
├── decisions.json
├── risks.json
├── action_items.json
├── blockers.json
├── feedback.json
└── project_history.json
```

Global memory at `~/.opserve/memory/_global/` for cross-project signals.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/analyze` | Trigger analysis for projects |
| `GET /api/dashboard` | Multi-project executive view |
| `GET /api/dashboard/{project_id}` | Single project view |
| `GET /api/events/history` | Poll for agent events |
| `GET /api/events/stream` | Live SSE stream |
| `POST /api/feedback` | Store feedback (accept/reject/edit) |
| `GET /api/memory/summary` | Company Memory summary |

## Event Types

Agents emit these events via `bus.emit()`:

- `agent_start` — agent begins
- `agent_complete` — agent finishes successfully
- `agent_error` — agent raised exception
- `analysis_start` — full analysis begins
- `analysis_complete` — full analysis finishes
- `analysis_error` — analysis failed
- `auto_trigger` — auto-poller detected new events
- `poller_error` — poller error (non-fatal)

Base44 polls `/api/events/history?since=HH:MM:SS PST` for real-time progress.

## Building New Connectors

1. Create `opserve_agents/connectors/my_source.py`
2. Subclass `BaseConnector`
3. Implement `fetch()` returning standard dict structure
4. Add to connector list in `team.py`

Example stub:
```python
class JiraConnector(BaseConnector):
    source_name = "jira"

    async def fetch(self, project_id: str, since: datetime | None = None) -> dict:
        # TODO: Call real Jira API
        return {
            "tasks": [...],
            "events": [],
            "messages": [],
            "notes": [],
            "documents": [],
            "errors": []
        }

    def is_configured(self) -> bool:
        return os.getenv("JIRA_API_KEY") is not None
```

## Perspective Review (Inside Role Translator)

The Role Translator runs an internal quality check on all recommendations:

```python
# Pseudocode
recommendations = generate_role_specific_outputs()

for rec in recommendations:
    if not has_owner(rec):
        return "Add owner"
    if not has_evidence(rec):
        return "Requires confirmation" or remove it
    if not has_deadline(rec):
        return "Add deadline"
    if is_vague_advice(rec):  # "improve communication"
        return "Be specific"

return polished_recommendations
```

The review prompt is embedded in the role_translator system prompt.

## Error Recovery

**Connector Error:**
Logged to `errors` array. Pipeline continues with remaining sources.

**Agent Error:**
Emitted to event bus. Error details available via `/api/events/history`. Pipeline stops.

**Poller Error:**
Caught and logged. Retries after 60 seconds. Does not crash server.

## Configuration

### Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...
PORT=8000  # default
```

### Auto-Poller

Interval in `team.py`:
```python
await start_auto_poller(interval_seconds=900)  # default 15 min
```

## Deployment

### Railway

1. Create new Railway project
2. Point to GitHub repo (`IrinaMira1/opserve`)
3. Set env vars (ANTHROPIC_API_KEY)
4. Deploy (Procfile handles it)

**Procfile:**
```
web: uvicorn opserve_agents.api_server:app --host 0.0.0.0 --port $PORT
```

**runtime.txt:**
```
python-3.11.7
```

### Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

uvicorn opserve_agents.api_server:app --reload
```

## Testing

### Unit Test a Single Agent

```python
import asyncio
from opserve_agents.agents.context_collector import ContextCollectorAgent

async def test():
    agent = ContextCollectorAgent()
    output = await agent._process(
        json.dumps({"tasks": [...]}),
        {"project_id": "Project Atlas"}
    )
    print(output)

asyncio.run(test())
```

### Test Full Pipeline

```bash
python opserve_agents/main.py
```

### Test API

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"project_ids": ["Project Atlas"], "use_mock": true}'

curl http://localhost:8000/api/events/history?since=00:00:00
```

## File Structure

```
opserve/
├── .env
├── .gitignore
├── requirements.txt
├── Procfile
├── runtime.txt
├── README.md
├── CLAUDE.md
└── opserve_agents/
    ├── __init__.py
    ├── main.py                    # CLI entrypoint
    ├── team.py                    # Pipeline + auto-poller
    ├── api_server.py              # FastAPI REST API
    ├── agents/
    │   ├── __init__.py
    │   ├── base_agent.py          # Abstract BaseAgent (from semiconductor-agents)
    │   ├── context_collector.py   # Agent 1
    │   ├── workflow_mapper.py     # Agent 2
    │   ├── risk_agent.py          # Agent 3
    │   ├── impact_analyzer.py     # Agent 4
    │   └── role_translator.py     # Agent 5 + perspective review
    ├── core/
    │   ├── __init__.py
    │   ├── events.py              # EventBus singleton (from semiconductor-agents)
    │   └── memory.py              # Company Memory (new)
    └── connectors/
        ├── __init__.py
        ├── base_connector.py      # Abstract BaseConnector
        ├── mock_data.py           # Project Atlas demo
        ├── trello.py              # Stub
        ├── google_calendar.py     # Stub
        ├── gmail.py               # Stub
        ├── google_sheets.py       # Stub
        └── meeting_notes.py       # Stub
```

## Dependencies

```
anthropic>=0.50.0
python-dotenv>=1.0.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
```

## See Also

- **GitHub**: https://github.com/IrinaMira1/opserve
- **Live API**: https://opserve-production.up.railway.app
- **API Docs**: https://opserve-production.up.railway.app/docs
