"""Ollama MCP server -- chat, generation, embedding, summarization, and classification
backed by a local Ollama daemon (`http://localhost:11434` by default)."""

from mcp.server.fastmcp import FastMCP

from .. import _runtime
from . import impl

mcp = FastMCP("ollama", port=8808)


@mcp.tool(name="llm.chat")
def chat(messages: list[impl.ChatMessage], model: str = "", format: dict | None = None) -> impl.ChatOut:
    """Send `messages` to the local chat model; `format` is an optional JSON Schema for structured output."""
    return impl.chat(messages, model=model, format=format)


@mcp.tool(name="llm.generate")
def generate(prompt: str, model: str = "") -> impl.GenerateOut:
    """Complete `prompt` with the local chat model (no conversation history)."""
    return impl.generate(prompt, model=model)


@mcp.tool(name="llm.embed")
def embed(text: str, model: str = "") -> impl.EmbedOut:
    """Embed `text` with the local embedding model."""
    return impl.embed(text, model=model)


@mcp.tool(name="llm.summarize")
def summarize(text: str, max_words: int = 150, model: str = "") -> impl.SummarizeOut:
    """Summarize `text` in at most `max_words` words."""
    return impl.summarize(text, max_words=max_words, model=model)


@mcp.tool(name="llm.classify")
def classify(text: str, labels: list[str], model: str = "") -> impl.ClassifyOut:
    """Classify `text` into exactly one of `labels`."""
    return impl.classify(text, labels, model=model)


app = _runtime.build_app(mcp)

if __name__ == "__main__":
    _runtime.run_main(mcp)
