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
    def __init__(self, name: str, system_prompt: str, model: str = "claude-haiku-4-5-20251001", use_mock: bool = False):
        self.name = name
        self.system_prompt = system_prompt
        self.model = model
        self.status = "idle"
        self.use_mock = use_mock
        self._client = anthropic.AsyncAnthropic()

    async def _call_claude(self, prompt: str, max_retries: int = 3) -> str:
        # In mock mode, return hardcoded responses per agent
        print(f"DEBUG: {self.name}._call_claude() entered with self.use_mock={self.use_mock}", flush=True)
        if self.use_mock:
            mock_response = self._get_mock_response()
            print(f"DEBUG: {self.name} returning mock response (length={len(mock_response)})", flush=True)
            return mock_response

        print(f"DEBUG: {self.name} calling real Claude API (use_mock={self.use_mock})", flush=True)
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
                    error_msg = f"{self.name}: Claude returned no text. Response content: {response.content}, Usage: {response.usage}"
                    print(f"ERROR: {error_msg}", flush=True)
                    raise RuntimeError(error_msg)
                if not text.strip():
                    raise ValueError(f"Empty Anthropic response for agent {self.name}")
                return text
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(f"{self.name} failed after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(2 ** attempt)

    def _get_mock_response(self) -> str:
        """Return hardcoded mock response for demo mode."""
        # Default empty response - subclasses override
        return "{}"

    async def run(self, content: str, metadata: dict | None = None, use_mock: bool = False) -> str:
        metadata = metadata or {}
        self.status = "working"
        self.use_mock = use_mock  # Override for this run
        print(f"DEBUG: {self.name}.run() called with use_mock={use_mock}", flush=True)

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
