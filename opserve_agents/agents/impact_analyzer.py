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
