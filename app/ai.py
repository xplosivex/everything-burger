"""Unified AI backend abstraction (Bring Your Own Key).

Supported backends:
  - mistral  (recommended)  https://console.mistral.ai
  - openai                   https://platform.openai.com
  - claude                   https://console.anthropic.com
  - ollama                   Ollama Cloud (https://ollama.com) or self-hosted
                             (OLLAMA_BASE_URL + optional OLLAMA_API_KEY)

Every generation stage calls `complete()` which routes to the configured
backend and returns plain text. Providers that don't support a feature
(e.g. `response_format` JSON mode on some models) degrade gracefully.
"""

import logging

from app.config import (
    AI_BACKEND,
    MISTRAL_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    OLLAMA_BASE_URL,
    OLLAMA_API_KEY,
    CONTENT_MODEL,
    STRUCTURE_MODEL,
    STYLING_MODEL,
    SUMMARY_MODEL,
)

logger = logging.getLogger(__name__)

# Default models per backend, per stage. The app resolves CONTENT_MODEL etc.
# as an override; otherwise it uses these.
_DEFAULT_MODELS = {
    'mistral': {
        'content': 'mistral-large-latest',
        'structure': 'codestral-latest',
        'styling': 'mistral-medium-latest',
        'summary': 'mistral-small-latest',
    },
    'openai': {
        'content': 'gpt-5.6-terra',
        'structure': 'gpt-5.6-terra',
        'styling': 'gpt-5.6-terra',
        'summary': 'gpt-5.6-luna',
    },
    'claude': {
        'content': 'claude-sonnet-5',
        'structure': 'claude-sonnet-5',
        'styling': 'claude-sonnet-5',
        'summary': 'claude-haiku-4-5',
    },
    'ollama': {
        'content': 'llama3.2',
        'structure': 'llama3.2',
        'styling': 'llama3.2',
        'summary': 'llama3.2',
    },
}

# User-configurable model override per stage.
_MODEL_OVERRIDES = {
    'content': CONTENT_MODEL,
    'structure': STRUCTURE_MODEL,
    'styling': STYLING_MODEL,
    'summary': SUMMARY_MODEL,
}


def resolve_model(stage):
    """Return the model name for a generation stage on the active backend."""
    override = _MODEL_OVERRIDES.get(stage, '')
    if override:
        return override
    return _DEFAULT_MODELS.get(AI_BACKEND, _DEFAULT_MODELS['mistral']).get(stage, '')


def complete(stage, messages, max_tokens=2000, temperature=0.8, top_p=None,
             response_format=None, json_mode=False):
    """Run a chat completion on the active backend.

    :param stage: one of 'content' | 'structure' | 'styling' | 'summary'
    :param messages: list of {"role": ..., "content": ...}
    :param max_tokens: max tokens to generate
    :param temperature: sampling temperature
    :param top_p: nucleus sampling (if supported)
    :param response_format: provider-specific format hint (e.g. {"type": "json_object"})
    :param json_mode: True to hint providers to return JSON (maps to response_format)
    :return: plain text response content
    """
    if json_mode and response_format is None:
        response_format = {'type': 'json_object'}

    backend = AI_BACKEND
    if backend == 'mistral':
        return _complete_mistral(stage, messages, max_tokens, temperature, top_p, response_format)
    if backend == 'openai':
        return _complete_openai(stage, messages, max_tokens, temperature, top_p, response_format)
    if backend == 'claude':
        return _complete_claude(stage, messages, max_tokens, temperature, top_p, json_mode)
    if backend == 'ollama':
        return _complete_ollama(stage, messages, max_tokens, temperature, json_mode)
    raise ValueError(f"Unsupported AI_BACKEND: {backend!r}")


def _complete_mistral(stage, messages, max_tokens, temperature, top_p, response_format):
    from mistralai.client import Mistral
    client = Mistral(api_key=MISTRAL_API_KEY)
    kwargs = dict(
        model=resolve_model(stage),
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if top_p is not None:
        kwargs['top_p'] = top_p
    if response_format is not None:
        kwargs['response_format'] = response_format
    response = client.chat.complete(**kwargs)
    return response.choices[0].message.content.strip()


def _complete_openai(stage, messages, max_tokens, temperature, top_p, response_format):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    kwargs = dict(
        model=resolve_model(stage),
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if top_p is not None:
        kwargs['top_p'] = top_p
    if response_format is not None:
        kwargs['response_format'] = response_format
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content.strip()


def _complete_claude(stage, messages, max_tokens, temperature, top_p, json_mode):
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    # Claude's API uses a single system prompt separate from messages.
    system_parts = [m['content'] for m in messages if m.get('role') == 'system']
    user_messages = [m for m in messages if m.get('role') != 'system']
    system = '\n\n'.join(system_parts) if system_parts else None

    kwargs = dict(
        model=resolve_model(stage),
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{'role': 'user', 'content': m['content']} for m in user_messages],
    )
    if system:
        kwargs['system'] = system
    if json_mode:
        # Modern structured-outputs API: constrain the response to a JSON
        # object (any shape) so the text block is always parseable JSON.
        kwargs['output_config'] = {
            'format': {
                'type': 'json_schema',
                'schema': {
                    'type': 'object',
                    'additionalProperties': True,
                },
            },
        }
    response = client.messages.create(**kwargs)
    return ''.join(block.text or '' for block in response.content).strip()


def _complete_ollama(stage, messages, max_tokens, temperature, json_mode):
    """Call an Ollama-compatible chat endpoint.

    Works with both a self-hosted Ollama server (no key) and Ollama Cloud
    (requires OLLAMA_API_KEY). Ollama Cloud serves the same /api/chat API
    at https://ollama.com; set OLLAMA_BASE_URL to it and provide a key.
    """
    import httpx
    headers = {}
    if OLLAMA_API_KEY:
        headers['Authorization'] = f'Bearer {OLLAMA_API_KEY}'
    format_arg = 'json' if json_mode else None
    payload = {
        'model': resolve_model(stage),
        'messages': messages,
        'stream': False,
        'options': {'temperature': temperature, 'num_predict': max_tokens},
    }
    if format_arg:
        payload['format'] = format_arg
    url = OLLAMA_BASE_URL.rstrip('/') + '/api/chat'
    resp = httpx.post(url, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return (data.get('message', {}) or {}).get('content', '').strip()
