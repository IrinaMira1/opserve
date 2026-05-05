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

    def _get_mock_response(self) -> str:
        """Mock response for demo mode."""
        return json.dumps({
            "risks": [
                {
                    "risk_id": "R-001",
                    "risk_title": "Critical task has no owner (T-47)",
                    "severity": "Critical",
                    "project": "Project Atlas",
                    "owner": None,
                    "department": "Operations",
                    "why_it_matters": "Supplier validation is blocking the Friday release. No one is assigned to follow up.",
                    "evidence": [
                        "Trello: T-47 'Validate supplier datasheet' has owner=null",
                        "Meeting notes: 'Action item assigned to team (no specific owner)'",
                        "Task is marked 'Blocked' status"
                    ],
                    "missing_context": ["Who should own this?", "What's the supplier's exact ETA?"],
                    "recommended_escalation": True,
                    "estimated_timeline_impact": "If not resolved by EOD Thursday, Friday release will slip",
                    "capacity_issue": "Alice and Bob available; Sarah overbooked"
                },
                {
                    "risk_id": "R-002",
                    "risk_title": "External supplier hasn't sent required file (3+ days overdue)",
                    "severity": "Critical",
                    "project": "Project Atlas",
                    "owner": "Alice Johnson",
                    "department": "External",
                    "why_it_matters": "Validation can't proceed without the supplier file. This is the critical path item.",
                    "evidence": [
                        "Gmail (3 days old): Supplier says 'We have not yet sent the required input file. Will confirm by EOD Thursday.'",
                        "Task status: Blocked",
                        "No follow-up confirmation received"
                    ],
                    "missing_context": ["Confirmed supplier ETA?", "Backup plan if file doesn't arrive?"],
                    "recommended_escalation": True,
                    "estimated_timeline_impact": "Must resolve by EOD Thursday or Friday release is at risk",
                    "capacity_issue": ""
                },
                {
                    "risk_id": "R-003",
                    "risk_title": "Owner (Sarah Chen) is overbooked Friday (6 meetings, 30-min free slot)",
                    "severity": "High",
                    "project": "Project Atlas",
                    "owner": "Sarah Chen",
                    "department": "Management",
                    "why_it_matters": "If Sarah is the backup owner for T-47, she has almost no time to work on it Friday.",
                    "evidence": [
                        "Calendar: 9:00-10:00 standup, 10:30-11:30 architecture review, 14:00-14:30 CEO meeting, 15:00-16:00 budget, 16:30-17:15 retrospective",
                        "Only free slot: 10:00-10:30 AM (30 minutes)",
                        "No evening availability shown"
                    ],
                    "missing_context": ["Is Sarah the backup?", "Can any meetings be moved?"],
                    "recommended_escalation": False,
                    "estimated_timeline_impact": "Limits decision-making availability Friday",
                    "capacity_issue": "Sarah overbooked; needs to delegate or reschedule"
                }
            ],
            "top_risks_summary": "CRITICAL: Task #47 has no owner AND supplier file is missing (3+ days). This blocks the entire Friday release. Requires immediate executive decision on owner assignment and supplier follow-up.",
            "overall_project_health": "Red",
            "memory_updates": []
        })
