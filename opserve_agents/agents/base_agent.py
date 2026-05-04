import asyncio
import os
import anthropic
from ..core.events import bus
from dotenv import load_dotenv

load_dotenv()

# Verify API key is available
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY not found in environment variables. Set it in Railway Variables.")


class BaseAgent:
    def __init__(self, name: str, system_prompt: str, model: str = "claude-haiku-4-5-20251001"):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.status = "idle"
        self._client = anthropic.AsyncAnthropic()

    async def _call_claude(self, prompt: str, max_retries: int = 3) -> str:
        for attempt in range(max_retries):
            try:
                response = await self._client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = next((b.text for b in response.content if b.type == "text"), None)
            if not text:
                raise RuntimeError(f"Claude returned no text content. Response: {response.model_dump()}")
            return text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"{self.name} failed after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    async def run(self, content: str, metadata: dict | None = None) -> str:
        metadata = metadata or {}
        self.status = "working"

        await bus.emit("agent_start", self.name, {
            "task": content[:200],
            "metadata": metadata,
        })

        try:
            result = await self._process(content, metadata)
            self.status = "idle"
            await bus.emit("agent_complete", self.name, {
                "result_preview": result[:300],
                "full_result": result,
            })
            return result
        except Exception as e:
            self.status = "error"
            await bus.emit("agent_error", self.name, {"error": str(e)})
            raise

    async def _process(self, content: str, metadata: dict) -> str:
        raise NotImplementedError
