export type Tool = "READ" | "SEARCH" | "WRITE" | "CREATE" | "DELETE" | "REINDEX" | "SETTINGS";

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
