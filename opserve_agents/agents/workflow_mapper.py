import json
from .base_agent import BaseAgent
from ..core.memory import memory

_SYSTEM = """You are the Workflow/Dependency Mapper agent for OPServe.

Your job:
1. Take the context from Context Collector
2. Map the project structure: tasks, owners, milestones, deadlines
3. Identify dependencies between tasks
4. Find handoffs and ownership
5. Detect unclear ownership, missing steps, and workflow gaps
6. Build a clean operational map from fragmented information

You are turning messy context into structured workflow understanding.

Output ONLY valid JSON. Return NOTHING else. No markdown, no explanation, just raw JSON:

{
  "project_id": "",
  "project_map": [],
  "owners": [],
  "dependencies": [],
  "handoffs": [],
  "unclear_ownership": [],
  "missing_steps": [],
  "status_conflicts": [],
  "workflow_summary": ""
}

CRITICAL: Your response MUST be valid JSON that can be parsed by Python's json.loads().
No markdown code blocks. No extra text. Only the JSON object.
"""


class WorkflowMapperAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="WorkflowMapper", system_prompt=_SYSTEM)

    async def _process(self, content: str, metadata: dict) -> str:
        project_id = metadata.get("project_id", "Unknown")

        # Read workflow history from memory
        workflow_context = memory.read(project_id, "project_history")
        workflow_context_str = json.dumps(workflow_context[-2:]) if workflow_context else "No prior workflows"

        prompt = f"""You received this context from the Context Collector for project: {project_id}

Context Data:
{content}

Prior Workflow Context:
{workflow_context_str}

Now map the complete workflow. Who owns what? What depends on what?
Where is ownership unclear? What steps might be missing?

Return structured JSON."""

        return await self._call_claude(prompt)

    def _get_mock_response(self) -> str:
        """Mock response for demo mode."""
        return json.dumps({
            "project_id": "Project Atlas",
            "project_map": [
                {"task_id": "T-45", "title": "Design review", "owner": "Alice Johnson", "status": "In Progress", "due": "Friday"},
                {"task_id": "T-46", "title": "Implementation complete", "owner": "Bob Smith", "status": "In Progress", "due": "Friday"},
                {"task_id": "T-47", "title": "Validate supplier datasheet", "owner": None, "status": "Blocked", "due": "Friday"}
            ],
            "owners": [
                {"name": "Alice Johnson", "assigned_tasks": 1, "capacity": "available"},
                {"name": "Bob Smith", "assigned_tasks": 1, "capacity": "available"},
                {"name": "Sarah Chen", "assigned_tasks": 0, "capacity": "overbooked", "notes": "6 meetings Friday"}
            ],
            "dependencies": [
                {"from": "T-47", "to": "supplier", "type": "external_dependency", "status": "unresolved"}
            ],
            "handoffs": [
                {"from": "supplier", "to": "Alice Johnson", "task": "T-47", "status": "waiting"}
            ],
            "unclear_ownership": ["T-47 (no owner assigned)"],
            "missing_steps": [
                "Confirm supplier ETA",
                "Assign backup owner for T-47",
                "Risk escalation decision"
            ],
            "status_conflicts": [],
            "workflow_summary": "3-task Friday milestone. Critical blocker: supplier datasheet (T-47) has no owner and file not received. Alice and Bob have capacity. Sarah overbooked."
        })
