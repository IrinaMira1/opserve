"""OPServe team coordinator.

Fixed sequential pipeline (no orchestrator):
1. Context Collector — read all sources
2. Workflow Mapper — map project structure
3. Risk Agent — detect risks
4. Impact Analyzer — estimate business impact
5. Role Translator — generate role-specific actions + perspective review

Dual trigger modes:
- Manual: run_analysis() called explicitly
- Automatic: auto_poller() runs every 15 seconds, detects new events
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from .agents.context_collector import ContextCollectorAgent
from .agents.workflow_mapper import WorkflowMapperAgent
from .agents.risk_agent import RiskAgent
from .agents.impact_analyzer import ImpactAnalyzerAgent
from .agents.role_translator import RoleTranslatorAgent
from .core.events import bus
from .core.memory import memory
from .connectors.mock_data import MockDataConnector

load_dotenv()

# Single instantiation of all agents
context_collector = ContextCollectorAgent()
workflow_mapper = WorkflowMapperAgent()
risk_agent = RiskAgent()
impact_analyzer = ImpactAnalyzerAgent()
role_translator = RoleTranslatorAgent()

# Mock data connector for MVP
mock_connector = MockDataConnector()


async def _fetch_all_sources(project_id: str, since: datetime | None = None) -> dict:
    """Fetch data from all configured connectors in parallel."""
    connectors = [mock_connector]  # Add real connectors here as they are implemented

    results = await asyncio.gather(
        *[c.fetch(project_id, since) for c in connectors if c.is_configured()],
        return_exceptions=True
    )

    # Merge all results
    merged = {
        "tasks": [],
        "events": [],
        "messages": [],
        "notes": [],
        "documents": [],
        "errors": []
    }

    for result in results:
        if isinstance(result, Exception):
            merged["errors"].append(str(result))
        elif isinstance(result, dict):
            for key in merged.keys():
                if key in result:
                    merged[key].extend(result[key])

    return merged


async def run_analysis(project_ids: list[str], use_mock: bool = False) -> dict:
    """Run the full OPServe pipeline for given projects.

    Args:
        project_ids: List of project IDs to analyze
        use_mock: If True, use mock data for all sources

    Returns:
        dict with analysis results for each project
    """
    results = {}

    for project_id in project_ids:
        await bus.emit("analysis_start", "Team", {
            "project": project_id,
            "trigger": "manual"
        })

        try:
            # Step 1: Context Collector
            raw_sources = await _fetch_all_sources(project_id)
            context_output = await context_collector.run(
                json.dumps(raw_sources, indent=2),
                {"project_id": project_id}
            )

            # Step 2: Workflow Mapper
            workflow_output = await workflow_mapper.run(
                context_output,
                {"project_id": project_id}
            )

            # Step 3: Risk Agent
            risk_output = await risk_agent.run(
                f"Context:\n{context_output}\n\nWorkflow:\n{workflow_output}",
                {"project_id": project_id}
            )

            # Step 4: Impact Analyzer
            impact_output = await impact_analyzer.run(
                risk_output,
                {"project_id": project_id}
            )

            # Step 5: Role Translator (with internal perspective review)
            final_output = await role_translator.run(
                f"Context:\n{context_output}\n\nWorkflow:\n{workflow_output}\n\nRisks:\n{risk_output}\n\nImpact:\n{impact_output}",
                {"project_id": project_id}
            )

            # Write any memory updates from agents
            try:
                final_json = json.loads(final_output)
            except json.JSONDecodeError:
                final_json = {"error": "Invalid JSON from final output", "raw": final_output[:500]}

            # Extract and write memory updates (skip if JSON parsing fails)
            for output_str in [context_output, workflow_output, risk_output, impact_output, final_output]:
                try:
                    agent_output = json.loads(output_str)
                except json.JSONDecodeError:
                    continue  # Skip invalid JSON
                if "memory_updates" in agent_output:
                    for update in agent_output.get("memory_updates", []):
                        category = update.get("category")
                        if category:
                            memory.append(project_id, category, update.get("entry", {}))

            results[project_id] = {
                "status": "success",
                "analysis": final_json,
                "timestamp": datetime.utcnow().isoformat()
            }

            await bus.emit("analysis_complete", "Team", {
                "project": project_id,
                "health": final_json.get("overall_project_health", "Unknown")
            })

        except Exception as e:
            results[project_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

            await bus.emit("analysis_error", "Team", {
                "project": project_id,
                "error": str(e)
            })

    return results


async def start_auto_poller(interval_seconds: int = 15):
    """Background task: check for new events every N seconds, trigger analysis if changed.

    Default: 15 seconds
    """
    last_scan = {}

    while True:
        try:
            projects = memory.get_all_projects()
            if not projects:
                projects = ["Project Atlas"]  # Demo default

            for project_id in projects:
                # Check if new events since last scan
                sources = await _fetch_all_sources(project_id, since=last_scan.get(project_id))

                if any(sources.get(k) for k in ["tasks", "events", "messages", "notes"]):
                    await bus.emit("auto_trigger", "Team", {
                        "project": project_id,
                        "reason": "New operational events detected"
                    })
                    result = await run_analysis([project_id])

                last_scan[project_id] = datetime.utcnow()

            await asyncio.sleep(interval_seconds)

        except Exception as e:
            await bus.emit("poller_error", "Team", {"error": str(e)})
            await asyncio.sleep(60)  # Wait 1 min before retrying


def start_poller_task():
    """Start auto-poller as background task (for FastAPI lifespan)."""
    return asyncio.create_task(start_auto_poller())
