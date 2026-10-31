"""
Unified AI / LLM Client for Vortex Studio Pro.
Supports:
1. Local Ollama (auto-detects installed models, e.g. qwen2.5, llama3.2, mistral, gemma, phi3)
2. Google Gemini API (via GEMINI_API_KEY / GOOGLE_API_KEY)
3. OpenAI API (via OPENAI_API_KEY)
4. Robust JSON parsing and heuristic fallback
"""

import os
import json
import re
import time
import requests
from typing import Dict, Any, List, Optional, Union

# Default endpoints and timeouts
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
REQUEST_TIMEOUT = int(os.environ.get("AI_REQUEST_TIMEOUT", "6"))

_cached_ollama_model: Optional[str] = None
_last_model_check: float = 0.0


def get_available_ollama_models() -> List[str]:
    """Queries Ollama for list of installed models."""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = [m.get("name") or m.get("model") for m in data.get("models", [])]
            return [m for m in models if m]
    except Exception:
        pass
    return []


def resolve_best_ollama_model(preferred: Optional[str] = None) -> Optional[str]:
    """
    Finds the best model available on Ollama.
    Checks user preference or environment variable, then installed models.
    """
    global _cached_ollama_model, _last_model_check
    
    # Check cache (valid for 30 seconds)
    if _cached_ollama_model and (time.time() - _last_model_check < 30) and not preferred:
        return _cached_ollama_model

    env_model = os.environ.get("AI_MODEL") or os.environ.get("OLLAMA_MODEL")
    installed = get_available_ollama_models()
    
    if not installed:
        return None

    if preferred and any(preferred in m for m in installed):
        _cached_ollama_model = next(m for m in installed if preferred in m)
        _last_model_check = time.time()
        return _cached_ollama_model

    if env_model and any(env_model in m for m in installed):
        _cached_ollama_model = next(m for m in installed if env_model in m)
        _last_model_check = time.time()
        return _cached_ollama_model

    # Preference ranking for viral shorts analysis & creative copy
    priorities = [
        "llama3.2", "llama3.1", "llama3",
        "mistral", "gemma2", "qwen2.5:1.5b",
        "qwen2.5:3b", "qwen2.5:7b", "qwen2.5",
        "phi3", "orca", "neural-chat"
    ]

    for p in priorities:
        for m in installed:
            if p in m.lower():
                _cached_ollama_model = m
                _last_model_check = time.time()
                return _cached_ollama_model

    # Fallback to the first installed model
    _cached_ollama_model = installed[0]
    _last_model_check = time.time()
    return _cached_ollama_model


def query_ollama(
    prompt: str,
    system: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = REQUEST_TIMEOUT
) -> Optional[str]:
    """Sends a generation request to the local Ollama instance."""
    chosen_model = resolve_best_ollama_model(preferred=model)
    if not chosen_model:
        return None

    payload: Dict[str, Any] = {
        "model": chosen_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": 300
        }
    }
    if system:
        payload["system"] = system

    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
            timeout=timeout
        )
        if resp.status_code == 200:
            return resp.json().get("response", "").strip()
    except Exception:
        pass
    return None


def query_gemini(
    prompt: str,
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.0-flash"
) -> Optional[str]:
    """Generates text via Google Gemini REST API if API key is configured."""
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    contents = []
    if system:
        contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system}"}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})

    try:
        resp = requests.post(
            url,
            json={"contents": contents, "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300}},
            timeout=6
        )
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception:
        pass
    return None


def query_openai(
    prompt: str,
    system: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: str = "gpt-4o-mini"
) -> Optional[str]:
    """Generates text via OpenAI API if API key is configured."""
    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        return None

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model_name, "messages": messages, "temperature": 0.7, "max_tokens": 300},
            timeout=6
        )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception:
        pass
    return None


def generate_ai_text(
    prompt: str,
    system: Optional[str] = None,
    temperature: float = 0.7,
    timeout: int = REQUEST_TIMEOUT
) -> Optional[str]:
    """
    Unified entry point. Tries:
    1. Gemini API (if key available)
    2. OpenAI API (if key available)
    3. Ollama local model (if running)
    Returns text response or None.
    """
    # 1. Cloud Gemini
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        res = query_gemini(prompt, system=system)
        if res:
            return res

    # 2. Cloud OpenAI
    if os.environ.get("OPENAI_API_KEY"):
        res = query_openai(prompt, system=system)
        if res:
            return res

    # 3. Local Ollama
    return query_ollama(prompt, system=system, temperature=temperature, timeout=timeout)


def extract_json_from_text(text: str) -> Optional[Union[Dict[str, Any], List[Any]]]:
    """
    Extracts and parses JSON object or array from LLM responses,
    safely handling markdown fences, trailing commas, and text preamble.
    """
    if not text:
        return None

    cleaned = text.strip()

    # Strip markdown code blocks
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Find [ ... ] for list
    start_arr = cleaned.find("[")
    end_arr = cleaned.rfind("]")
    if start_arr != -1 and end_arr > start_arr:
        candidate = cleaned[start_arr:end_arr + 1]
        try:
            return json.loads(candidate)
        except Exception:
            # Fix single quotes
            try:
                candidate_fixed = candidate.replace("'", '"')
                return json.loads(candidate_fixed)
            except Exception:
                pass

    # Find { ... } for dict
    start_obj = cleaned.find("{")
    end_obj = cleaned.rfind("}")
    if start_obj != -1 and end_obj > start_obj:
        candidate = cleaned[start_obj:end_obj + 1]
        try:
            return json.loads(candidate)
        except Exception:
            try:
                candidate_fixed = candidate.replace("'", '"')
                return json.loads(candidate_fixed)
            except Exception:
                pass

    return None

