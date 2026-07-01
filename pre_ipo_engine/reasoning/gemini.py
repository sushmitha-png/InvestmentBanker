import json
import re
import os
import time
from dotenv import load_dotenv
import google.generativeai as genai

# Load .env from project root (two levels up from this file)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env'))

def init_gemini(project_id: str = None, location: str = None):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Please set it in the .env file.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.5-pro")

def ask_gemini(model, prompt: str, temperature: float = 0.2, max_tokens: int = 8192) -> str:
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
    )
    return response.text

def _extract_json_str(response_text: str) -> str:
    """Extract JSON string from model response, handling markdown fences."""
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        return json_match.group(1)
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        return json_match.group(0)
    return response_text.strip()

def ask_gemini_json(model, prompt: str, retries: int = 2, temperature: float = 0.2) -> dict:
    """
    Ask Gemini and parse JSON response.
    Retries up to `retries` times on parse failure.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            response_text = ask_gemini(model, prompt, temperature=temperature)
            json_str = _extract_json_str(response_text)

            # Try direct parse
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Fix common issues and retry
                json_str = json_str.strip()
                if json_str.startswith('```'):
                    json_str = json_str[3:]
                if json_str.endswith('```'):
                    json_str = json_str[:-3]
                json_str = json_str.strip()
                return json.loads(json_str)

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            if attempt < retries:
                time.sleep(1 * (attempt + 1))
                continue
    raise ValueError(f"Failed to parse JSON after {retries + 1} attempts. Last error: {last_error}")
