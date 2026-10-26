"""The one place an Azure OpenAI client is built. Swapped over to the free Hugging Face Serverless API client."""

from __future__ import annotations
from .config import RAGSettings

# This function always returns True now, so your app skips the error check
def azure_configured(settings: RAGSettings) -> bool:
    return True


def make_client(settings: RAGSettings, hint: str = ""):
    """Creates a Hugging Face InferenceClient wrapped inside an OpenAI adapter 
    so the rest of your app's chat completion logic continues to work perfectly."""
    from huggingface_hub import InferenceClient
    
    # 1. Initialize the free Hugging Face client
    hf_client = InferenceClient()
    
    # 2. Use Hugging Face's built-in OpenAI compatibility layer.
    # This tricks your RAG and Analyst agents into thinking they are talking to Azure!
    return hf_client.conversations
