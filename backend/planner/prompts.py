"""Chat message builders for the Planner's three LLM calls: draft, replan, verify.

Plain functions returning `list[dict]` chat messages -- no templating engine,
since the structure is fixed and short.
"""

from __future__ import annotations

from agents.base import StepResult
from memory.schemas import MemoryContext

from .plan import Plan

PLANNING_SYSTEM_PROMPT = (
    "You are a planning module for a file-management assistant. Given a "
    "user's task and a list of available tools, produce a short plan: an "
    "ordered list of tool calls (with arguments) that will accomplish the "
    "task. Only use tools from the provided list, and only include steps "
    "that are necessary. Use fully-qualified tool names exactly as given "
    '(e.g. "search.keyword"). If the task doesn\'t need any tool, return an '
    "empty steps list."
)

VERIFICATION_SYSTEM_PROMPT = (
    "You judge whether a task was accomplished. Given the original task and "
    "the results of the steps taken, decide whether the goal is satisfied "
    "and explain why in one or two sentences."
)


def _render_memory_context(memory_context: MemoryContext | None) -> str:
    if memory_context is None:
        return ""
    blocks = []
    if memory_context.recent_tasks:
        blocks.append("Recent tasks:\n" + "\n".join(f"- {t}" for t in memory_context.recent_tasks))
    if memory_context.preferences:
        prefs = "\n".join(f"- {k}: {v}" for k, v in memory_context.preferences.items())
        blocks.append(f"User preferences:\n{prefs}")
    return ("\n\n".join(blocks) + "\n\n") if blocks else ""


def build_planning_prompt(
    task: str, tools_context: str, memory_context: MemoryContext | None = None
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Available tools:\n{tools_context}\n\n{_render_memory_context(memory_context)}Task: {task}",
        },
    ]


def build_replan_prompt(
    task: str, tools_context: str, prior_plan: Plan, results: list[StepResult]
) -> list[dict[str, str]]:
    results_text = "\n".join(
        f"- {r.step.tool}({r.step.arguments}) -> "
        + ("ERROR: " + (r.error_message or "unknown error") if r.is_error else f"OK: {r.tool_result}")
        for r in results
    )
    return [
        {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Available tools:\n{tools_context}\n\nTask: {task}\n\n"
                f"Prior plan: {prior_plan.model_dump_json()}\n\n"
                f"Results so far (some failed):\n{results_text}\n\n"
                "Produce a revised plan for the remaining work, accounting for the failures above."
            ),
        },
    ]


def build_verification_prompt(task: str, results: list[StepResult]) -> list[dict[str, str]]:
    results_text = "\n".join(
        f"- {r.step.tool}({r.step.arguments}) -> "
        + ("ERROR: " + (r.error_message or "unknown error") if r.is_error else f"OK: {r.tool_result}")
        for r in results
    )
    return [
        {"role": "system", "content": VERIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Task: {task}\n\nStep results:\n{results_text}"},
    ]
