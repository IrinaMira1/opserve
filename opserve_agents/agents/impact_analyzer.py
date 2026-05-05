import json
from .base_agent import BaseAgent
from ..core.memory import memory

_SYSTEM = """You are the Impact Analyzer agent for OPServe.

Your job:
1. Take detected risks from the Risk Agent
2. Estimate the operational and business impact
3. Prioritize risks by urgency and business importance
4. Identify which risks need executive attention
5. Explain why each risk matters in business language
6. Estimate timeline and revenue impact when possible

You are translating raw risks into business impact language.

Output ONLY valid JSON with this exact structure:
{
  "impact_summary": "",
  "prioritized_risks": [],
  "executive_attention_needed": [],
  "estimated_business_impact": "",
  "estimated_delivery_impact": "",
  "decision_needed": "",
  "memory_updates": []
}

CRITICAL: Your response MUST be valid JSON that can be parsed by Python's json.loads().
No markdown code blocks. No extra text. Only the JSON object.

Remember:
- Be clear about business consequences
- Prioritize by what matters most (revenue, delivery, reputation)
- Flag executive decisions that are needed
- Do not use emojis or special symbols
"""


class ImpactAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ImpactAnalyzer", system_prompt=_SYSTEM)

    async def _process(self, content: str, metadata: dict) -> str:
        project_id = metadata.get("project_id", "Unknown")
        business_context = metadata.get("business_context", "Not specified")

        # Read business decisions from memory
        decisions = memory.read(project_id, "decisions")
        decision_context = json.dumps(decisions[-2:]) if decisions else "No prior decisions"

        prompt = f"""Analyze the business impact of these risks for project: {project_id}

Risk Analysis:
{content}

Business Context: {business_context}

Prior Decisions:
{decision_context}

What is the timeline impact? Revenue impact? Reputation risk?
Which risks need executive decision-making?

Return structured JSON with business impact analysis."""

        return await self._call_claude(prompt)

    def _get_mock_response(self) -> str:
        """Mock response for demo mode."""
        return json.dumps({
            "impact_summary": "Friday release is at HIGH RISK of slipping. Root cause: supplier dependency unresolved + no task owner. Estimated impact: 24-48 hour delay, customer commitment at risk.",
            "prioritized_risks": [
                {
                    "risk_id": "R-001",
                    "priority": 1,
                    "business_impact": "Release delay → customer commitment miss → reputation damage",
                    "timeline_impact": "If not resolved by EOD Thursday, release slips to Monday (3-day delay)"
                },
                {
                    "risk_id": "R-002",
                    "priority": 2,
                    "business_impact": "Supplier fails to deliver → cannot validate → release blocked",
                    "timeline_impact": "If file arrives Friday morning, only 2-hour window to validate"
                },
                {
                    "risk_id": "R-003",
                    "priority": 3,
                    "business_impact": "Owner unavailable Friday → decision delays",
                    "timeline_impact": "Limits ability to execute Friday (but R-001/R-002 more critical)"
                }
            ],
            "executive_attention_needed": [
                "URGENT: Assign owner to T-47 TODAY (not Friday)",
                "URGENT: Call supplier for confirmed ETA on file (not email)",
                "URGENT: Develop contingency if supplier misses Thursday deadline",
                "Possible actions: delay release, validate with partial data, find alternative input"
            ],
            "estimated_business_impact": "Revenue risk if customer expects Friday delivery. Reputation risk if release slips without notice. $X revenue at risk (depends on customer contract).",
            "estimated_delivery_impact": "High probability (70%) of Friday slip. Likely Monday delivery instead (3-day delay).",
            "decision_needed": "Executive decision required: (1) Assign owner immediately, (2) Confirm supplier ETA, (3) Approve contingency plan if needed.",
            "memory_updates": []
        })
