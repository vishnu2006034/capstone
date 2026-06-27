import sys
from types import ModuleType
from google import genai
from google.genai import types
from app.core.config import settings

class LocalAgentConfig:
    """Configures the agent environment locally."""
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class MockResponse:
    """Mock agent response wrapper."""
    def __init__(self, text_val: str):
        self._text = text_val
        
    async def text(self) -> str:
        return self._text

class Agent:
    """
    Mock Google ADK Agent that routes reasoning requests 
    to the official Gemini API client.
    """
    def __init__(self, config: LocalAgentConfig = None, **kwargs):
        self.config = config
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def chat(self, prompt: str, response_schema=None) -> MockResponse:
        """
        Interacts with the Gemini model. Supports structured outputs.
        """
        config_args = {}
        if response_schema:
            config_args["response_mime_type"] = "application/json"
            config_args["response_schema"] = response_schema

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(**config_args)
        )
        return MockResponse(response.text)

# Inject mock into python system modules
google_mod = sys.modules.get("google")
if not google_mod:
    google_mod = ModuleType("google")
    sys.modules["google"] = google_mod

antigravity_mod = ModuleType("google.antigravity")
google_mod.antigravity = antigravity_mod
sys.modules["google.antigravity"] = antigravity_mod

# Expose classes inside mock namespace
antigravity_mod.Agent = Agent
antigravity_mod.LocalAgentConfig = LocalAgentConfig
