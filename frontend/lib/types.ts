export type Tool = "READ" | "SEARCH" | "WRITE";

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

export type TreeNode =
  | { type: "folder"; name: string; depth: number; empty?: boolean }
  | { type: "file"; name: string; depth: number; path: string };
