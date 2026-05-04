import json
from .base_agent import BaseAgent
from ..core.memory import memory

_SYSTEM = """You are the Risk Agent for OPServe, an operational intelligence system.

Your job:
1. Analyze context and workflow data
2. Detect execution risks that could impact the project
3. Assign severity: Low, Medium, High, Critical
4. Connect each risk to concrete evidence
5. Estimate timeline and business impact
6. Identify whether escalation is needed

Risks you detect:
- Missed deadlines or approaching deadlines with no progress
- Unclear ownership or overloaded owners
- Unresolved dependencies
- Supplier or external party delays
- Communication gaps or conflicting information
- Decisions not made
- Missing information or context

Output ONLY valid JSON with this exact structure:
{
  "risks": [
    {
      "risk_id": "",
      "risk_title": "",
      "severity": "Low|Medium|High|Critical",
      "project": "",
      "owner": "",
      "department": "",
      "why_it_matters": "",
      "evidence": [],
      "missing_context": [],
      "recommended_escalation": boolean,
      "estimated_timeline_impact": "",
      "capacity_issue": ""
    }
  ],
  "top_risks_summary": "",
  "overall_project_health": "Green|Yellow|Red",
  "memory_updates": []
}

CRITICAL: Your response MUST be valid JSON that can be parsed by Python's json.loads().
No markdown code blocks. No extra text. Only the JSON object.

Remember:
- Every risk must be backed by evidence
- Be specific about timeline impact
- Flag escalation only when truly needed
- Do not use emojis or special symbols
"""


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RiskAgent", system_prompt=_SYSTEM)

    async def _process(self, content: str, metadata: dict) -> str:
        project_id = metadata.get("project_id", "Unknown")

        # Read historical risks to detect recurrence
        risk_history = memory.read(project_id, "risks")
        risk_context = json.dumps(risk_history[-3:]) if risk_history else "No prior risks recorded"

        prompt = f"""Analyze this context and workflow for project: {project_id}

Context and Workflow Data:
{content}

Prior Risk History (recurring risks?):
{risk_context}

What execution risks do you see? What could break before the deadline?
Which risks need immediate escalation?

Be specific with evidence and timeline impact. Return structured JSON."""

        return await self._call_claude(prompt)
