"""OrganizationAgent -- moves/renames/creates files, classifying/deciding via `llm.*`.

Allow-list per `mcp_architecture.md` #10.2: the `filesystem` namespace in
full, plus `llm.chat`/`llm.classify` (not all of `llm.*`) -- same
broad-namespace-plus-itemized-llm-tools pattern as `SearchAgent`.
"""

from .base import BaseAgent


class OrganizationAgent(BaseAgent):
    name = "organization"
    allowed_namespaces = frozenset({"filesystem"})
    allowed_tools = frozenset({"llm.chat", "llm.classify"})
