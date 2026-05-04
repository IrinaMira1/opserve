# OPServe — Operational Intelligence Platform

An operational brain for semiconductor and hardware teams. OPServe sits above existing tools (Trello, Google Calendar, Gmail, Sheets, meeting notes, documents) and turns fragmented operational context into clear risk signals, impact analysis, and role-specific checklists.

Not a chatbot. Not a project management tool. An **execution visibility and operational risk detection system** for complex teams.

## What OPServe Does

- **Reads operational context** from multiple sources (tasks, calendars, messages, documents)
- **Maps project workflows** (who owns what, what depends on what)
- **Detects execution risks** (missed deadlines, unclear ownership, unresolved dependencies, supplier delays)
- **Estimates business impact** (timeline impact, revenue risk, reputation risk)
- **Generates role-specific checklists** (executives, operations, engineering, suppliers) with actionable next steps
- **Runs automatically** (every 15 minutes) or on demand

## Live Server (Railway)

| Endpoint | URL |
|---|---|
| **API** | https://opserve-production.up.railway.app |
| **API Docs** | https://opserve-production.up.railway.app/docs |
| **Health** | https://opserve-production.up.railway.app/health |

## Quick Start

### CLI (Local Testing)

```bash
cd opserve_agents
python main.py
```

Runs the default Project Atlas demo scenario locally. Outputs structured analysis with role-specific checklists.

### API (Local)

```bash
uvicorn opserve_agents.api_server:app --reload
```

Then:

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"project_ids": ["Project Atlas"], "use_mock": true}'
```

## Architecture

**Five-Agent Sequential Pipeline:**

1. **Context Collector** — Reads all sources in parallel, extracts tasks, decisions, action items, blockers
2. **Workflow Mapper** — Maps project structure, ownership, dependencies, handoffs
3. **Risk Agent** — Detects execution risks with evidence and severity (Low/Medium/High/Critical)
4. **Impact Analyzer** — Estimates business impact, prioritizes risks, flags executive decisions
5. **Role Translator** — Generates role-specific summaries and checklists with perspective review

**Company Memory:** Shared context layer (not an agent). Stores decisions, risks, action items, blockers, feedback, project history. Agents read from it for historical context, write updates to it.

**Dual Triggers:**
- Manual: `POST /api/analyze` endpoint
- Automatic: Background poller runs every 15 minutes, detects new events, triggers analysis if anything changed

**Multi-Project from Day One:** Analyze one or many projects. Executive dashboard shows all. Cross-project risk signals detected (same supplier, same owner blocking multiple projects).

## Data Sources (MVP)

MVP ships with mock data connector (Project Atlas scenario). Future connectors (stubs provided):

- Trello
- Google Calendar
- Gmail
- Google Sheets
- AI Meeting Notes

Add new sources by implementing the `BaseConnector` interface. No agent changes needed.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/analyze` | Trigger analysis. Body: `{"project_ids": ["..."], "use_mock": true}` |
| GET | `/api/dashboard` | Multi-project executive dashboard |
| GET | `/api/dashboard/{project_id}` | Single project dashboard |
| GET | `/api/events/history` | Poll agent progress. `?since=HH:MM:SS%20PST` |
| GET | `/api/events/stream` | Live SSE event stream |
| POST | `/api/feedback` | Store feedback on recommendations |
| GET | `/api/memory/summary` | Company Memory summary |
| GET | `/health` | Health check |
| GET | `/docs` | Interactive API docs |

## Demo Scenario: Project Atlas

Realistic hardcoded scenario showing OPServe's risk detection:

- **Trello**: 3 critical tasks for Friday milestone. Task #47 "Validate supplier datasheet" has no owner, due Friday.
- **Google Calendar**: Sarah Chen (likely owner) has 6 meetings Friday, 1 free slot (10:00-10:30am).
- **Gmail**: Supplier thread (3 days old) says they haven't sent the required file yet.
- **Google Sheets**: Project row shows status "In Progress", 40% complete, last updated Tuesday.
- **Meeting Notes**: Wednesday standup discussed the blocker. Action item assigned to "team" (no specific owner).

**OPServe Output:**
- Health: RED
- Top Risk: CRITICAL — supplier input missing, owner unclear, Friday deadline
- Evidence: 4 sources corroborate the same blocker
- Executive Decision: Assign backup owner today, confirm supplier ETA
- Operations Checklist: 5 concrete action items
- Engineering Checklist: 3 technical next steps
- Supplier Request: Draft message requesting status and deadline confirmation

## Configuration

### API Key

Set `ANTHROPIC_API_KEY` in `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Auto-Poller Interval

Default: 15 minutes. Change in `team.py`:

```python
await start_auto_poller(interval_seconds=600)  # 10 minutes
```

## Company Memory Structure

Stored at `~/.opserve/memory/<project_id>/`:

- `decisions.json` — past decisions with owner, date, outcome
- `risks.json` — historical risks with severity, resolution, recurrence
- `action_items.json` — open and closed action items
- `blockers.json` — recurring blockers by project, owner, type
- `feedback.json` — user feedback on recommendations (accept/reject/edit)
- `project_history.json` — project snapshots and status changes

## How to Use in Production

1. Integrate real connectors (Trello API, Google Calendar OAuth, etc.)
2. Deploy to Railway
3. Set `ANTHROPIC_API_KEY` in Railway environment variables
4. Configure auto-poller interval based on your needs
5. Build a dashboard (Base44 recommended) to consume the API
6. Users click "Analyze Operational State" or let the auto-poller run

## Error Handling

- **Connector errors**: Logged and skipped. Pipeline continues with available sources.
- **Agent errors**: Emitted to event bus. Full error details available via `/api/events/history`.
- **API errors**: Return 500 with error message. Check agent output via events endpoint.

## Development Notes

- Agents: Subclasses of `BaseAgent`
- Company Memory: Not an agent. Shared context layer. Agents read/write to it.
- Events: All agent activity emitted to `bus` for real-time tracking.
- No database needed. JSON files + in-memory event bus.
- Fully async. Uses `asyncio.gather()` for parallel source fetching within Context Collector.

## See Also

- **CLAUDE.md** — Development documentation and architecture details
- **Anthropic SDK**: https://github.com/anthropics/anthropic-sdk-python
- **FastAPI**: https://fastapi.tiangolo.com
- **OPServe GitHub**: https://github.com/IrinaMira1/opserve
