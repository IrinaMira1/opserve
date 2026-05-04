import json
from .base_agent import BaseAgent
from ..core.memory import memory

_SYSTEM = """You are the Context Collector agent for OPServe, an operational intelligence system.

Your job:
1. Read structured data from multiple sources (Trello, Calendar, Gmail, Sheets, meeting notes)
2. Summarize what is happening across the project RIGHT NOW
3. Extract tasks, decisions, action items, and blockers
4. Identify missing context
5. Update Company Memory with new operational context

You are not making judgments or detecting risks yet. You are simply collecting and organizing what is happening.

Output ONLY valid JSON. Return NOTHING else. No markdown, no explanation, just raw JSON:

{
  "project_id": "",
  "new_context_summary": "",
  "source_updates": [],
  "extracted_tasks": [],
  "extracted_decisions": [],
  "extracted_action_items": [],
  "possible_blockers": [],
  "missing_context": [],
  "memory_updates": []
}

CRITICAL: Your response MUST be valid JSON that can be parsed by Python's json.loads().
No markdown code blocks. No extra text. Only the JSON object.
- Extract dates, owners, and status exactly as they appear
- Flag anything that seems incomplete or unclear
- Do not use emojis or special symbols
"""


class ContextCollectorAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ContextCollector", system_prompt=_SYSTEM)

    async def _process(self, content: str, metadata: dict) -> str:
        project_id = metadata.get("project_id", "Unknown")
        include_history = metadata.get("include_history", True)

        # Read project history from memory
        memory_summary = ""
        if include_history:
            hist = memory.summary(project_id)
            memory_summary = f"\n\nProject Memory (recent context):\n{json.dumps(hist, indent=2)}"

        prompt = f"""Analyze this operational data for project: {project_id}

Raw Data from all sources:
{content}
{memory_summary}

Extract and organize all operational context. What is the project state right now?
Who is doing what? What is blocked? What decisions are pending?

Return structured JSON."""

        return await self._call_claude(prompt)
