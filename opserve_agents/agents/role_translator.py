import json
from .base_agent import BaseAgent
from ..core.memory import memory

_SYSTEM = """You are the Role Translator agent for OPServe.

Your job:
1. Take all previous analysis (context, workflow, risks, impact)
2. Generate role-specific summaries and checklists
3. Create actionable next steps for each role
4. Translate business impact into role-specific language
5. Run internal perspective review on all recommendations

Roles you translate for:
- executive: C-level, decisions, business impact, timeline
- operations: project managers, execution, blockers, owners, checklists
- engineering: technical leads, implementation, dependencies, technical risks
- external_partner: suppliers, vendors, requested actions

Output ONLY valid JSON with this exact structure:
{
  "role_specific_outputs": {
    "executive": {
      "summary": "",
      "decision_needed": "",
      "business_impact": "",
      "checklist": []
    },
    "operations": {
      "summary": "",
      "blockers": [],
      "owners": [],
      "checklist": []
    },
    "engineering": {
      "summary": "",
      "technical_next_steps": [],
      "checklist": []
    },
    "external_partner": {
      "summary": "",
      "requested_action": "",
      "checklist": []
    }
  },
  "final_recommendation": "",
  "confidence_score": 0.0,
  "missing_context": [],
  "evidence_used": [],
  "perspective_review_notes": ""
}

CRITICAL: Your response MUST be valid JSON that can be parsed by Python's json.loads().
No markdown code blocks. No extra text. Only the JSON object.

PERSPECTIVE REVIEW (internal quality check):
Before returning, review each recommendation:
- Has an owner?
- Has concrete evidence (not vague)?
- Has deadline or urgency?
- Is specific and actionable (not generic advice)?
- Correct risk level?

If a recommendation fails the check, improve or remove it.

Remember:
- Every checklist item should be specific and actionable
- Each decision should have a deadline
- Each action should have an owner
- Do not use emojis or special symbols
"""


class RoleTranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RoleTranslator", system_prompt=_SYSTEM)

    async def _process(self, content: str, metadata: dict) -> str:
        project_id = metadata.get("project_id", "Unknown")

        # Read role preferences from memory (if any)
        feedback = memory.read(project_id, "feedback")
        feedback_context = json.dumps(feedback[-2:]) if feedback else "No prior feedback"

        prompt = f"""Create role-specific outputs for project: {project_id}

All Analysis (context, workflow, risks, impact):
{content}

Prior Feedback on Recommendations:
{feedback_context}

Now translate this into specific, actionable next steps for each role.

CRITICAL: Run perspective review on each recommendation before returning.
- Is it vague? Rewrite it to be specific.
- Does it lack an owner or deadline? Add one.
- Does it lack evidence? Remove it.
- Is it generic advice ("improve communication")? Delete it.

Return high-quality, perspective-reviewed JSON."""

        return await self._call_claude(prompt)
