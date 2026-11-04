"""The one place an Azure OpenAI client is built. Swapped over to the free Hugging Face Serverless API client. (This code hasnt been confirmed)

from __future__ import annotations
from .config import RAGSettings

# This function always returns True now, so your app skips the error check
def azure_configured(settings: RAGSettings) -> bool:
    return True


def make_client(settings: RAGSettings, hint: str = ""):
    Creates a Hugging Face InferenceClient wrapped inside an OpenAI adapter 
    so the rest of your app's chat completion logic continues to work perfectly.
    from huggingface_hub import InferenceClient
    
    # 1. Initialize the free Hugging Face client
    hf_client = InferenceClient()
    
    # 2. Use Hugging Face's built-in OpenAI compatibility layer.
    # This tricks your RAG and Analyst agents into thinking they are talking to Azure!
    return hf_client.conversations"""

"""The one place an Azure OpenAI client is built. Every LLM use (RAG embeddings, RAG rule
extraction, the explanation writer, the analyst agent) goes through here, so the five
AZURE_OPENAI_* variables in .env.example are the single source of truth."""

from __future__ import annotations

from .config import RAGSettings

DEFAULT_HINT = "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in .env (see docs/AZURE_SETUP.md)."


def azure_configured(settings: RAGSettings) -> bool:
    return bool(settings.azure_openai_endpoint and settings.azure_openai_api_key)


def make_client(settings: RAGSettings, hint: str = DEFAULT_HINT):
    """AzureOpenAI client with a request timeout and 2 retries. Raises RuntimeError (never prints
    the key) if Azure is not configured."""
    if not azure_configured(settings):
        raise RuntimeError(hint)
    from openai import AzureOpenAI

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        timeout=settings.azure_timeout,
        max_retries=2,
    )
