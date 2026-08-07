import json
from typing import Dict, Any, Tuple
import httpx
from loguru import logger

from app.core.config import settings

# Attempt to import Gemini SDK if installed
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class OllamaClient:
    """Interface to communicate with local Ollama service for zero-cost semantic models."""

    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    async def generate(self, prompt: str, system_instruction: str = None) -> Tuple[str, int, int]:
        """Send prompt to local model. Returns (response_text, input_tokens, output_tokens)."""
        url = f"{self.host}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if system_instruction:
            payload["system"] = system_instruction

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    response_text = data.get("response", "")
                    
                    # Ollama returns token count parameters in some formats
                    prompt_eval_count = data.get("prompt_eval_count", len(prompt) // 4)
                    eval_count = data.get("eval_count", len(response_text) // 4)
                    
                    return response_text, prompt_eval_count, eval_count
                else:
                    logger.warning(f"Ollama server returned error status {response.status_code}.")
                    raise ValueError(f"Ollama failure: {response.text}")
        except Exception as e:
            logger.error(f"Failed contacting Ollama model at {url}: {e}")
            raise ConnectionError(f"Ollama unavailable: {e}") from e


class GeminiClient:
    """Interface to communicate with Cloud Google Gemini API for complex executive narration."""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if GEMINI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.active = True
            logger.info("Gemini Cloud client configured successfully.")
        else:
            self.active = False
            logger.warning("Gemini Cloud client is not configured or google-generativeai is missing.")

    async def generate(self, prompt: str, system_instruction: str = None) -> Tuple[str, int, int]:
        """Sends analytical context to cloud model.

        Returns (response_text, input_tokens, output_tokens).
        """
        if not self.active:
            raise ValueError("Cloud Gemini API not configured or credential key missing.")

        try:
            # Prepare contents
            contents = []
            if system_instruction:
                contents.append(f"System Directives:\n{system_instruction}")
            contents.append(prompt)
            
            # Since Gemini SDK is synchronous/blocking for generate_content, we run it in a thread pool executor.
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Execute SDK generate content
            response = await loop.run_in_executor(
                None, 
                lambda: self.model.generate_content(contents)
            )
            
            response_text = response.text
            
            # Token counts approximation (or exact if metadata is returned)
            input_tokens = len(prompt) // 4
            output_tokens = len(response_text) // 4
            
            return response_text, input_tokens, output_tokens
        except Exception as e:
            logger.error(f"Gemini API query execution failed: {e}")
            raise RuntimeError(f"Gemini API failure: {e}") from e


ollama_client = OllamaClient()
gemini_client = GeminiClient()
