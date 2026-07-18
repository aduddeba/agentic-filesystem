"""SearchAgent -- the first (and for now only) registered agent.

Allow-list per `mcp_architecture.md` #10.2: the `search` and `semantic`
namespaces in full, plus the single cross-namespace tool `llm.classify`
(so it can classify search results) without opening up the rest of `llm.*`.
"""

from .base import BaseAgent


class SearchAgent(BaseAgent):
    name = "search"
    allowed_namespaces = frozenset({"search", "semantic"})
    allowed_tools = frozenset({"llm.classify"})
