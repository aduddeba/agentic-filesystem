import type { SearchEntry, SemanticEntry, TaskOutcome, TaskStatus, TreeNode } from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? `Request failed: ${response.status}`);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

interface TreeNodeDto {
  path: string;
  name: string;
  is_dir: boolean;
  depth: number;
  size: number;
}

function toTreeNode(dto: TreeNodeDto): TreeNode {
  return dto.is_dir
    ? { type: "folder", name: dto.name, depth: dto.depth, path: dto.path }
    : { type: "file", name: dto.name, depth: dto.depth, path: dto.path };
}

export interface Stats {
  file_count: number;
  directory_count: number;
  total_size: number;
}

export function fetchTree(): Promise<TreeNode[]> {
  return request<TreeNodeDto[]>("/api/files/tree").then((entries) => entries.map(toTreeNode));
}

export function fetchStats(): Promise<Stats> {
  return request<Stats>("/api/files/stats");
}

export function fetchFileContent(path: string): Promise<string> {
  return request<{ path: string; content: string }>(
    `/api/files/content?path=${encodeURIComponent(path)}`
  ).then((res) => res.content);
}

export function createEntry(path: string, type: "file" | "directory", content = ""): Promise<TreeNode> {
  return request<TreeNodeDto>("/api/files", {
    method: "POST",
    body: JSON.stringify({ path, type, content }),
  }).then(toTreeNode);
}

export function updateFileContent(path: string, content: string): Promise<void> {
  return request<void>(`/api/files/content?path=${encodeURIComponent(path)}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export function deleteEntry(path: string): Promise<void> {
  return request<void>(`/api/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });
}

export function renameEntry(path: string, newPath: string): Promise<TreeNode> {
  return request<TreeNodeDto>("/api/files", {
    method: "PATCH",
    body: JSON.stringify({ path, new_path: newPath }),
  }).then(toTreeNode);
}

export function searchFiles(query: string): Promise<SearchEntry[]> {
  return request<{ path: string; line: number; text: string }[]>(
    `/api/files/search?q=${encodeURIComponent(query)}`
  ).then((matches) => matches.map((m) => ({ file: m.path, line: m.line, text: m.text })));
}

export function searchSemantic(query: string, mode: "hybrid" | "vector" = "hybrid"): Promise<SemanticEntry[]> {
  return request<{ path: string; text: string; score: number }[]>(
    `/api/files/search/semantic?q=${encodeURIComponent(query)}&mode=${mode}`
  ).then((matches) => matches.map((m) => ({ file: m.path, text: m.text, score: m.score })));
}

export interface ReindexResult {
  indexed: number;
  failed: number;
}

export function reindexAll(): Promise<ReindexResult> {
  return request<ReindexResult>("/api/files/reindex", { method: "POST" });
}

interface TaskStepDto {
  tool: string;
  arguments: Record<string, unknown>;
  is_error: boolean;
  result: Record<string, unknown> | null;
  error_message: string | null;
}

interface TaskOutDto {
  task: string;
  status: TaskStatus;
  message: string;
  steps: TaskStepDto[];
}

function toTaskOutcome(dto: TaskOutDto): TaskOutcome {
  return {
    task: dto.task,
    status: dto.status,
    message: dto.message,
    steps: dto.steps.map((s) => ({
      tool: s.tool,
      arguments: s.arguments,
      isError: s.is_error,
      result: s.result,
      errorMessage: s.error_message,
    })),
  };
}

export function submitTask(task: string): Promise<TaskOutcome> {
  return request<TaskOutDto>("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ task }),
  }).then(toTaskOutcome);
}

export function fetchSettings(): Promise<{ storage_root: string }> {
  return request<{ storage_root: string }>("/api/settings");
}

export function updateStorageRoot(path: string): Promise<{ storage_root: string }> {
  return request<{ storage_root: string }>("/api/settings", {
    method: "PUT",
    body: JSON.stringify({ storage_root: path }),
  });
}
