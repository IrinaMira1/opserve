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
    print(f"DEBUG: run_analysis() called with use_mock={use_mock}, project_ids={project_ids}", flush=True)
    results = {}

    # Fast path: if use_mock, return hardcoded demo results immediately
    if use_mock:
        print(f"DEBUG: use_mock=True, returning hardcoded demo results immediately (no agents)", flush=True)
        for project_id in project_ids:
            print(f"DEBUG: Creating demo results for {project_id}", flush=True)
            demo_analysis = {
                "project_id": project_id,
                "risks": [
                    {
                        "risk_id": "R-001",
                        "risk_title": "Critical task has no owner (T-47)",
                        "severity": "Critical",
                        "evidence": ["Task #47 has no assigned owner", "Supplier file missing (3+ days overdue)"]
                    },
                    {
                        "risk_id": "R-002",
                        "risk_title": "External supplier hasn't sent required file",
                        "severity": "Critical",
                        "evidence": ["Email 3 days old: supplier says file not sent yet"]
                    }
                ],
                "action_items": [
                    {"role": "executive", "task": "Assign owner to T-47 today", "status": "open"},
                    {"role": "operations", "task": "Call supplier for confirmed ETA", "status": "open"},
                    {"role": "engineering", "task": "Prepare contingency validation plan", "status": "open"}
                ],
                "blockers": [
                    {"blocker": "No owner assigned to critical task T-47", "owner": None},
                    {"blocker": "Supplier file not received (3+ days)", "owner": "Supplier"},
                    {"blocker": "Sarah Chen overbooked Friday", "owner": "Sarah Chen"}
                ],
                "decisions": [
                    {"decision": "Assign backup owner to T-47", "owner": "Executive", "status": "pending"},
                    {"decision": "Contact supplier for ETA confirmation", "owner": "Operations", "status": "pending"}
                ],
                "overall_health": "Red"
            }
            results[project_id] = {
                "status": "success",
                "analysis": demo_analysis,
                "timestamp": datetime.utcnow().isoformat()
            }
            # Write demo data to memory (don't fail if memory fails)
            try:
                memory.append(project_id, "risks", demo_analysis["risks"][0])
                memory.append(project_id, "risks", demo_analysis["risks"][1])
                for item in demo_analysis["action_items"]:
                    memory.append(project_id, "action_items", item)
                for blocker in demo_analysis["blockers"]:
                    memory.append(project_id, "blockers", blocker)
                for decision in demo_analysis["decisions"]:
                    memory.append(project_id, "decisions", decision)
            except Exception as e:
                print(f"WARNING: Failed to write to memory: {str(e)}", flush=True)
        return results

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
                {"project_id": project_id},
                use_mock=use_mock
            )
            print(f"DEBUG: ContextCollector output length: {len(context_output)}, first 100 chars: {context_output[:100]}", flush=True)

            # Step 2: Workflow Mapper
            workflow_output = await workflow_mapper.run(
                context_output,
                {"project_id": project_id},
                use_mock=use_mock
            )
            print(f"DEBUG: WorkflowMapper output length: {len(workflow_output)}, first 100 chars: {workflow_output[:100]}", flush=True)

            # Step 3: Risk Agent
            risk_output = await risk_agent.run(
                f"Context:\n{context_output}\n\nWorkflow:\n{workflow_output}",
                {"project_id": project_id},
                use_mock=use_mock
            )
            print(f"DEBUG: RiskAgent output length: {len(risk_output)}, first 100 chars: {risk_output[:100]}", flush=True)

            # Step 4: Impact Analyzer
            impact_output = await impact_analyzer.run(
                risk_output,
                {"project_id": project_id},
                use_mock=use_mock
            )
            print(f"DEBUG: ImpactAnalyzer output length: {len(impact_output)}, first 100 chars: {impact_output[:100]}", flush=True)

            # Step 5: Role Translator (with internal perspective review)
            final_output = await role_translator.run(
                f"Context:\n{context_output}\n\nWorkflow:\n{workflow_output}\n\nRisks:\n{risk_output}\n\nImpact:\n{impact_output}",
                {"project_id": project_id},
                use_mock=use_mock
            )
            print(f"DEBUG: RoleTranslator output length: {len(final_output)}, first 100 chars: {final_output[:100]}", flush=True)

            # Write any memory updates from agents
            if not final_output or not final_output.strip():
                error_msg = f"RoleTranslator returned empty output"
                print(f"ERROR: {error_msg}", flush=True)
                final_json = {"error": "Empty output from RoleTranslator"}
            else:
                try:
                    final_json = json.loads(final_output)
                except json.JSONDecodeError as e:
                    error_msg = f"JSON parse error from RoleTranslator: {str(e)}. Output length={len(final_output)}, first 500={final_output[:500]}"
                    print(f"ERROR: {error_msg}", flush=True)
                    final_json = {"error": "Invalid JSON from final output", "raw": final_output[:500]}
                except Exception as e:
                    error_msg = f"Exception parsing RoleTranslator output: {str(e)}"
                    print(f"ERROR: {error_msg}", flush=True)
                    final_json = {"error": str(e)}

            # Extract and write to memory (auto-extract risks, action items, decisions)
            if not risk_output or not risk_output.strip():
                print(f"ERROR: RiskAgent returned empty output", flush=True)
            else:
                try:
                    risk_json = json.loads(risk_output)
                    if "risks" in risk_json:
                        for risk in risk_json.get("risks", []):
                            memory.append(project_id, "risks", risk)
                        print(f"DEBUG: Wrote {len(risk_json.get('risks', []))} risks to memory", flush=True)
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse RiskAgent output: {str(e)}, output_length={len(risk_output)}, first_200={risk_output[:200]}", flush=True)
                except Exception as e:
                    print(f"ERROR: Exception processing RiskAgent output: {str(e)}", flush=True)

            if not final_output or not final_output.strip():
                print(f"ERROR: RoleTranslator returned empty output", flush=True)
            else:
                try:
                    final_json_for_memory = json.loads(final_output)
                    # Extract action items from role_specific_outputs
                    role_outputs = final_json_for_memory.get("role_specific_outputs", {})
                    action_count = 0
                    for role, role_data in role_outputs.items():
                        if isinstance(role_data, dict) and "checklist" in role_data:
                            for item in role_data.get("checklist", []):
                                action_item = {
                                    "role": role,
                                    "task": item,
                                    "status": "open",
                                    "created": datetime.utcnow().isoformat()
                                }
                                memory.append(project_id, "action_items", action_item)
                                action_count += 1
                    if action_count > 0:
                        print(f"DEBUG: Wrote {action_count} action items to memory", flush=True)
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse RoleTranslator output: {str(e)}, output_length={len(final_output)}, first_200={final_output[:200]}", flush=True)
                except Exception as e:
                    print(f"ERROR: Exception processing RoleTranslator output: {str(e)}", flush=True)

            # Also extract explicit memory_updates if present
            for output_str in [context_output, workflow_output, risk_output, impact_output, final_output]:
                try:
                    agent_output = json.loads(output_str)
                except json.JSONDecodeError:
                    continue
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
