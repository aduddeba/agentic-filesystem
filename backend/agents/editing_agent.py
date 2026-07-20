"""EditingAgent -- reads/writes files and extracts document text, using `llm.*` to draft edits.

Allow-list per `mcp_architecture.md` #10.2: `filesystem` + `document` in
full, plus `llm.chat`/`llm.classify`.
"""

from .base import BaseAgent


class EditingAgent(BaseAgent):
    name = "editing"
    allowed_namespaces = frozenset({"filesystem", "document"})
    allowed_tools = frozenset({"llm.chat", "llm.classify"})
