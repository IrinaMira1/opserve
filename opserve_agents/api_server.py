"""OPServe REST API — Operational Intelligence Platform.

Live server: https://opserve-production.up.railway.app
API docs: https://opserve-production.up.railway.app/docs
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from opserve_agents.team import run_analysis, start_poller_task
from opserve_agents.core.events import bus
from opserve_agents.core.memory import memory

load_dotenv()

PST = timezone(timedelta(hours=-8))


def pst_now() -> str:
    return datetime.now(PST).strftime("%H:%M:%S %Z")


class AnalyzeRequest(BaseModel):
    project_ids: list[str]
    use_mock: bool = True


class AnalyzeResponse(BaseModel):
    status: str
    results: dict


class FeedbackRequest(BaseModel):
    project_id: str
    rec_id: str
    action: str
    note: str = ""


poller_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start auto-poller on startup, clean up on shutdown."""
    global poller_task
    poller_task = start_poller_task()
    yield
    if poller_task:
        poller_task.cancel()


app = FastAPI(
    title="OPServe API",
    description="Operational Intelligence Platform for semiconductor and hardware teams",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    """Trigger analysis for one or more projects.

    Returns results from all 5 agents plus dashboard sections.
    """
    if not req.project_ids:
        raise HTTPException(status_code=400, detail="project_ids cannot be empty")

    try:
        results = await run_analysis(req.project_ids, use_mock=req.use_mock)
        return AnalyzeResponse(
            status="success",
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/dashboard")
async def get_dashboard_multi():
    """Multi-project executive dashboard."""
    projects = memory.get_all_projects()
    if not projects:
        projects = ["Project Atlas"]

    dashboard = {
        "timestamp": pst_now(),
        "projects": {}
    }

    for project_id in projects:
        summary = memory.summary(project_id)
        dashboard["projects"][project_id] = {
            "recent_risks": summary.get("risks", [])[-3:],
            "open_action_items": [a for a in summary.get("action_items", []) if a.get("status") != "closed"],
            "recent_decisions": summary.get("decisions", [])[-2:]
        }

    return dashboard


@app.get("/api/dashboard/{project_id}")
async def get_dashboard_project(project_id: str):
    """Single project dashboard."""
    summary = memory.summary(project_id)
    return {
        "timestamp": pst_now(),
        "project": project_id,
        "risks": summary.get("risks", []),
        "action_items": summary.get("action_items", []),
        "blockers": summary.get("blockers", []),
        "decisions": summary.get("decisions", [])
    }


@app.get("/api/events/history")
async def events_history(since: str | None = None):
    """Poll for event history since a given time."""
    events = bus.get_history()

    if not since:
        return {"events": [_event_to_dict(e) for e in events[-50:]]}

    try:
        since_time = datetime.strptime(since, "%H:%M:%S %Z").time()
    except ValueError:
        since_time = None

    filtered = []
    for event in events:
        event_dict = _event_to_dict(event)
        if since_time is None:
            filtered.append(event_dict)
        else:
            try:
                event_time = datetime.strptime(event_dict["time"], "%H:%M:%S %Z").time()
                if event_time > since_time:
                    filtered.append(event_dict)
            except ValueError:
                filtered.append(event_dict)

    return {"events": filtered}


def _event_to_dict(event: dict) -> dict:
    """Convert internal event to user-friendly dict with PST timestamp."""
    event_type = event.get("event", "")
    agent = event.get("agent", "")
    data = event.get("data", {})

    status = "in_progress"
    message = ""

    if event_type == "agent_start":
        status = "in_progress"
        message = f"Starting: {str(data.get('task', ''))[:100]}"
    elif event_type == "agent_complete":
        status = "completed"
        message = f"Completed: {agent}"
    elif event_type == "agent_error":
        status = "failed"
        message = str(data.get("error", "Unknown error"))[:100]
    elif event_type == "analysis_start":
        status = "in_progress"
        message = f"Analyzing {data.get('project', '')} — {data.get('trigger', '')}"
    elif event_type == "analysis_complete":
        status = "completed"
        message = f"Analysis complete: {data.get('project', '')} — Health: {data.get('health', 'Unknown')}"
    elif event_type == "analysis_error":
        status = "failed"
        message = f"Analysis failed: {str(data.get('error', ''))[:80]}"
    elif event_type == "auto_trigger":
        status = "in_progress"
        message = f"Auto-triggered: {data.get('project', '')} — {data.get('reason', '')}"
    else:
        return None

    return {
        "time": pst_now(),
        "agent": agent,
        "status": status,
        "message": message,
    }


@app.post("/api/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Store feedback on a recommendation."""
    feedback_entry = {
        "rec_id": req.rec_id,
        "action": req.action,
        "note": req.note,
        "timestamp": datetime.utcnow().isoformat()
    }

    memory.append(req.project_id, "feedback", feedback_entry)

    return {
        "status": "recorded",
        "feedback": feedback_entry
    }


@app.get("/api/memory/summary")
async def get_memory_summary():
    """Get Company Memory summary across all projects."""
    projects = memory.get_all_projects()
    if not projects:
        projects = ["Project Atlas"]

    summary = {}
    for project_id in projects:
        summary[project_id] = memory.summary(project_id)

    return {
        "timestamp": pst_now(),
        "memory": summary
    }


@app.get("/api/events/stream")
async def event_stream(request: Request):
    """Live SSE event stream."""
    queue = bus.subscribe()

    async def generator():
        for event in bus.get_history()[-20:]:
            event_dict = _event_to_dict(event)
            if event_dict:
                yield f"data: {json.dumps(event_dict)}\n\n"

        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_dict = _event_to_dict(event)
                    if event_dict:
                        yield f"data: {json.dumps(event_dict)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            bus.unsubscribe(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "OPServe API", "version": "1.0.0"}


@app.get("/")
async def root():
    return {
        "service": "OPServe — Operational Intelligence Platform",
        "version": "1.0.0",
        "endpoints": {
            "POST /api/analyze": "Trigger analysis for projects",
            "GET /api/dashboard": "Multi-project executive dashboard",
            "GET /api/dashboard/{project_id}": "Single project dashboard",
            "GET /api/events/history": "Poll for events (?since=HH:MM:SS%20PST)",
            "GET /api/events/stream": "Live SSE event stream",
            "POST /api/feedback": "Submit feedback on recommendations",
            "GET /api/memory/summary": "Company Memory summary",
            "GET /health": "Health check",
            "GET /docs": "Interactive API documentation",
        },
    }


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
