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

    def _get_mock_response(self) -> str:
        """Mock response for demo mode."""
        return json.dumps({
            "role_specific_outputs": {
                "executive": {
                    "summary": "Friday release at HIGH RISK (70% slip probability). Root cause: supplier input missing + no task owner. Requires immediate decision.",
                    "decision_needed": "Approve contingency plan: (1) Assign owner to T-47 by EOD today, (2) Contact supplier for confirmed ETA, (3) If file delayed, decide: delay release vs. validate partial data.",
                    "business_impact": "Customer commitment at risk. $X revenue impact if slip.",
                    "checklist": [
                        "URGENT - Call supplier directly by 2pm today for ETA confirmation (not email)",
                        "URGENT - Assign specific owner to T-47 by EOD today (recommend Alice Johnson or backup)",
                        "By EOD Thursday - Receive supplier file and validate (or trigger contingency)",
                        "Friday morning - Execute validation test or contingency plan",
                        "By Friday 5pm - Make go/no-go release decision"
                    ]
                },
                "operations": {
                    "summary": "T-47 (Validate supplier datasheet) is BLOCKED with no owner. Supplier hasn't sent file (3+ days). Only T-45 and T-46 on track.",
                    "blockers": [
                        "T-47: No owner assigned",
                        "T-47: Supplier file not received (3+ days overdue)",
                        "Sarah Chen: Overbooked Friday (6 meetings, 30-min free slot)"
                    ],
                    "owners": [
                        "Alice Johnson: Available (recommend assign T-47 to her)",
                        "Bob Smith: Available",
                        "Sarah Chen: Overbooked (keep as escalation only)"
                    ],
                    "checklist": [
                        "TODAY - Assign Alice Johnson as owner of T-47, notify her immediately",
                        "TODAY - Send supplier follow-up: 'Per our conversation, need file by EOD Thursday. Confirm ETA or escalate to your manager.'",
                        "Thursday 4pm - Check supplier file receipt, begin validation if received",
                        "Thursday 10pm - Report T-47 status to exec team",
                        "Friday 8am - Execute validation test (or activate contingency)"
                    ]
                },
                "engineering": {
                    "summary": "T-45 (Design review) and T-46 (Implementation) on track. T-47 blocked waiting for supplier input.",
                    "technical_next_steps": [
                        "T-45: Alice - Complete design review by Friday 10am, document any changes",
                        "T-46: Bob - Complete implementation by Friday 2pm, prepare for validation",
                        "T-47: Await supplier datasheet, then run validation tests (estimated 2-4 hours)",
                        "Contingency: If file delayed, prepare alternate validation (mock data or partial test)"
                    ],
                    "checklist": [
                        "Thursday EOD - Confirm all T-45 and T-46 deliverables ready",
                        "Friday morning - Receive supplier file (or trigger contingency)",
                        "Friday 9am-1pm - Run validation tests on T-47",
                        "Friday 2pm - Validation complete or contingency activated",
                        "Friday 3pm - All go/no-go sign-offs collected"
                    ]
                },
                "external_partner": {
                    "summary": "Supplier (vendor) has not sent required datasheet (3+ days overdue). This is blocking our Friday release.",
                    "requested_action": "Send datasheet file by EOD Thursday, or confirm new ETA immediately.",
                    "checklist": [
                        "TODAY - Call supplier manager directly: 'We need the datasheet by EOD Thursday for our Friday release. Confirm you can deliver or escalate.'",
                        "If confirmed: Provide preferred file location and format",
                        "If delayed: Ask for specific ETA and backup contact",
                        "Thursday 6pm - Verify file received, test receipt",
                        "If file doesn't arrive: Activate backup plan (our validation continues Monday)"
                    ]
                }
            },
            "final_recommendation": "URGENT ACTIONS (TODAY): (1) Assign Alice Johnson to own T-47, (2) Call supplier with ETA demand, (3) Prepare contingency plan. THURSDAY: Confirm file receipt and validate. FRIDAY: Execute or contingency. Current release at risk but recoverable with immediate action.",
            "confidence_score": 0.95,
            "missing_context": [
                "Customer contract terms (hard vs. soft Friday deadline?)",
                "Supplier relationship/leverage (can we escalate?)",
                "Alternative data sources (if supplier fails completely)"
            ],
            "evidence_used": [
                "Trello: T-47 no owner, Blocked status",
                "Gmail: Supplier 3+ days overdue",
                "Calendar: Sarah overbooked",
                "Meeting notes: Action item unassigned",
                "Sheets: 40% complete, not on track for Friday"
            ],
            "perspective_review_notes": "All recommendations are specific, have owners/deadlines, and reference concrete evidence. No generic advice. Prioritized by timeline impact (supplier ETA is most critical). Contingency planned."
        })
