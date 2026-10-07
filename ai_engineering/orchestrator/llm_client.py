from ..rag.azure_client import make_client
from ..rag.azure_errors import call_azure
from ..rag.config import get_settings


class LLMClient:
    """Azure OpenAI chat wrapper for the explanation agent. Reads the same AZURE_OPENAI_* variables
    as the RAG (see .env.example); `generate(prompt)` keeps its original interface."""

    def __init__(self, settings=None, client=None):
        self.settings = settings or get_settings()
        self.client = client or make_client(self.settings)
        self.model = self.settings.chat_deployment  # the Azure deployment name

    def generate(self, prompt: str, system: str | None = None) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        response = call_azure(
            lambda: self.client.chat.completions.create(model=self.model, messages=messages, temperature=0.2),
            self.model,
            "chat",
        )
        return response.choices[0].message.content
