export type Tool = "READ" | "SEARCH" | "WRITE" | "CREATE" | "DELETE" | "REINDEX" | "SETTINGS" | "TASK";

export interface Activity {
  tool: Tool;
  detail: string;
  ts: number;
}

export interface SearchEntry {
  file: string;
  line: number;
  text: string;
}

export interface SemanticEntry {
  file: string;
  text: string;
  score: number;
}

export type TreeNode =
  | { type: "folder"; name: string; depth: number; path: string }
  | { type: "file"; name: string; depth: number; path: string };

export type TaskStatus = "completed" | "partial" | "failed";

export interface TaskStepEntry {
  tool: string;
  arguments: Record<string, unknown>;
  isError: boolean;
  result: Record<string, unknown> | null;
  errorMessage: string | null;
}

export interface TaskOutcome {
  task: string;
  status: TaskStatus;
  message: string;
  steps: TaskStepEntry[];
}
