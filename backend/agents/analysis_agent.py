"""AnalysisAgent -- extracts/embeds document content and summarizes/classifies it via `llm.*`.

Allow-list per `mcp_architecture.md` #10.2: `document` + `embedding` in
full, plus `llm.chat`/`llm.summarize`/`llm.classify`.
"""

from .base import BaseAgent


class AnalysisAgent(BaseAgent):
    name = "analysis"
    allowed_namespaces = frozenset({"document", "embedding"})
    allowed_tools = frozenset({"llm.chat", "llm.summarize", "llm.classify"})
