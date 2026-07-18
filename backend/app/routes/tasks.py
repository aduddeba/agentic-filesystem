"""REST endpoint for submitting a task to the Orchestrator."""

from fastapi import APIRouter, HTTPException

from ..mcp_runtime import get_orchestrator
from ..schemas import TaskIn, TaskOut, TaskStepOut

router = APIRouter(prefix="/api")


@router.post("/tasks", response_model=TaskOut)
async def create_task(body: TaskIn) -> TaskOut:
    if body.tool is None and not body.task.strip():
        raise HTTPException(status_code=400, detail="either `task` or `tool` is required")

    try:
        orchestrator = await get_orchestrator()
    except Exception as exc:  # noqa: BLE001 - surfaced as a clear 503, not a bare 500
        raise HTTPException(
            status_code=503, detail=f"planning/orchestration layer unavailable: {exc}"
        ) from None

    outcome = await orchestrator.run_task(
        body.task or f"Run {body.tool} directly", fixed_tool=body.tool, fixed_arguments=body.arguments
    )
    return TaskOut(
        task=outcome.task,
        status=outcome.status,
        message=outcome.message,
        steps=[
            TaskStepOut(
                tool=result.step.tool,
                arguments=result.step.arguments,
                is_error=result.is_error,
                result=result.tool_result,
                error_message=result.error_message,
            )
            for result in outcome.step_results
        ],
    )
