import json
import re
import os
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

def ask_gemini(model, prompt: str) -> str:
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.2,
            "max_output_tokens": 5000
        }
    )
    return response.text

def ask_gemini_json(model, prompt: str) -> dict:
    """
    Ask Gemini and parse JSON response.
    Handles cases where response may have markdown code blocks.
    """
    response_text = ask_gemini(model, prompt)
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
    else:
        # Try to find JSON object directly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            json_str = response_text.strip()
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # If parsing fails, try to fix common issues
        json_str = json_str.strip()
        if json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}")
