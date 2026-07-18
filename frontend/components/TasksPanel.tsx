"use client";

import { useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { ApiError, submitTask } from "../lib/api";
import type { TaskOutcome, TaskStatus } from "../lib/types";

interface Props {
  hidden: boolean;
  onLogTask: (task: string, status: TaskStatus) => void;
}

const STATUS_LABEL: Record<TaskStatus, string> = {
  completed: "Completed",
  partial: "Partially completed",
  failed: "Failed",
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  return typeof value === "string" ? value : JSON.stringify(value);
}

export default function TasksPanel({ hidden, onLogTask }: Props) {
  const [task, setTask] = useState("");
  const [loading, setLoading] = useState(false);
  const [outcome, setOutcome] = useState<TaskOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  function runTask() {
    const q = task.trim();
    if (!q || loading) return;

    const id = ++requestId.current;
    setLoading(true);
    setError(null);

    submitTask(q)
      .then((result) => {
        if (id !== requestId.current) return;
        setOutcome(result);
        onLogTask(q, result.status);
      })
      .catch((e) => {
        if (id !== requestId.current) return;
        setOutcome(null);
        setError(e instanceof ApiError ? e.message : "Failed to submit task");
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    setTask(e.target.value);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") runTask();
  }

  return (
    <div id="panelTasks" style={{ display: hidden ? "none" : "flex" }}>
      <div className="search-box">
        <input
          type="text"
          value={task}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Describe what you want done, e.g. “find TODO comments in the repo”…"
          autoComplete="off"
        />
        <div className="search-note">
          Sent to the Planner/Orchestrator (<code>POST /api/tasks</code>) — plans and runs via the local LLM and
          registered agents. Requires the MCP server cluster and Ollama to be running.
        </div>
      </div>

      <div className="search-meta">
        <span>
          {loading
            ? "Running…"
            : outcome
            ? `${STATUS_LABEL[outcome.status]} — ${outcome.steps.length} step${outcome.steps.length === 1 ? "" : "s"}`
            : "Type a task and press Enter to run it."}
        </span>
        <button type="button" className="btn primary" onClick={runTask} disabled={loading || !task.trim()}>
          Run
        </button>
      </div>

      <div className="pane-body">
        {error && <div className="empty-state">{error}</div>}

        {!error && outcome && (
          <div className="result" data-task-status={outcome.status}>
            <div className="rfile">
              <b>{STATUS_LABEL[outcome.status]}</b>
            </div>
            <div className="rtext">{outcome.message}</div>
          </div>
        )}

        {!error &&
          outcome?.steps.map((step, idx) => (
            <div className="result" key={idx} data-task-status={step.isError ? "failed" : "completed"}>
              <div className="rfile">
                <b>{step.tool}</b>
                <span className="rscore">{step.isError ? "error" : "ok"}</span>
              </div>
              <div className="rtext">
                {formatValue(step.arguments)}
                {step.isError ? `\n\n${step.errorMessage ?? "unknown error"}` : step.result ? `\n\n${formatValue(step.result)}` : ""}
              </div>
            </div>
          ))}

        {!error && !loading && !outcome && (
          <div className="empty-state">Nothing run yet — describe a task above.</div>
        )}
      </div>
    </div>
  );
}
