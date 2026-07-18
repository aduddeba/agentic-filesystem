"""Implementation behind the Ollama MCP server -- wraps the local Ollama HTTP daemon
for chat, generation, embedding, summarization, and classification.

`.summarize()` and `.classify()` have no native Ollama endpoint -- they're
prompted `chat()` calls with a JSON-schema `format` so the response is
reliably structured, not free-form text that needs fragile parsing.
"""

from __future__ import annotations

import json
from typing import TypedDict

import ollama

from app.config import settings


class ChatMessage(TypedDict):
    role: str
    content: str


class ChatOut(TypedDict):
    message: ChatMessage


class GenerateOut(TypedDict):
    response: str


class EmbedOut(TypedDict):
    embedding: list[float]


class SummarizeOut(TypedDict):
    summary: str


class ClassifyOut(TypedDict):
    label: str
    confidence: float


def _client() -> ollama.Client:
    return ollama.Client(host=settings.ollama_host)


def chat(messages: list[ChatMessage], model: str = "", format: dict | None = None) -> ChatOut:
    """Send `messages` to the local chat model; `format` is an optional JSON Schema for structured output."""
    response = _client().chat(model=model or settings.ollama_chat_model, messages=messages, format=format)
    return ChatOut(message=ChatMessage(role=response.message.role, content=response.message.content or ""))


def generate(prompt: str, model: str = "") -> GenerateOut:
    """Complete `prompt` with the local chat model (no conversation history)."""
    response = _client().generate(model=model or settings.ollama_chat_model, prompt=prompt)
    return GenerateOut(response=response.response)


def embed(text: str, model: str = "") -> EmbedOut:
    """Embed `text` with the local embedding model."""
    response = _client().embed(model=model or settings.ollama_embed_model, input=text)
    return EmbedOut(embedding=list(response.embeddings[0]))


def summarize(text: str, max_words: int = 150, model: str = "") -> SummarizeOut:
    """Summarize `text` in at most `max_words` words."""
    prompt = (
        f"Summarize the following text in at most {max_words} words. "
        "Respond with only the summary, no preamble.\n\n" + text
    )
    response = _client().chat(model=model or settings.ollama_chat_model, messages=[{"role": "user", "content": prompt}])
    return SummarizeOut(summary=(response.message.content or "").strip())


def classify(text: str, labels: list[str], model: str = "") -> ClassifyOut:
    """Classify `text` into exactly one of `labels`, using the local chat model for structured JSON output."""
    if len(labels) < 2:
        raise ValueError("classify requires at least 2 labels")

    schema = {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": labels},
            "confidence": {"type": "number"},
        },
        "required": ["label", "confidence"],
    }
    prompt = f"Classify the text into exactly one of these labels: {labels}.\n\nText: {text}"
    response = _client().chat(
        model=model or settings.ollama_chat_model,
        messages=[{"role": "user", "content": prompt}],
        format=schema,
    )
    data = json.loads(response.message.content or "{}")

    label = data.get("label")
    if label not in labels:
        match = next((candidate for candidate in labels if candidate.lower() == str(label).lower()), None)
        if match is None:
            raise ValueError(f"model returned label {label!r}, not one of {labels}")
        label = match

    confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    return ClassifyOut(label=label, confidence=confidence)
