import type { SearchEntry, TreeNode } from "./types";

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
