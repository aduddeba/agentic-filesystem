import type { TreeNode } from "./types";

export const TREE: TreeNode[] = [
  { type: "folder", name: "agentic-filesystem/", depth: 0 },
  { type: "folder", name: "backend/", depth: 1 },
  { type: "folder", name: "tools/", depth: 2 },
  { type: "folder", name: "filesystem/", depth: 3 },
  { type: "file", name: "__init__.py", depth: 4, path: "backend/tools/filesystem/__init__.py" },
  { type: "file", name: "read.py", depth: 4, path: "backend/tools/filesystem/read.py" },
  { type: "file", name: "search.py", depth: 4, path: "backend/tools/filesystem/search.py" },
  { type: "file", name: "write.py", depth: 4, path: "backend/tools/filesystem/write.py" },
  { type: "folder", name: "tests/", depth: 2 },
  { type: "file", name: "test_read.py", depth: 3, path: "backend/tests/test_read.py" },
  { type: "file", name: "test_search.py", depth: 3, path: "backend/tests/test_search.py" },
  { type: "file", name: "test_write.py", depth: 3, path: "backend/tests/test_write.py" },
  { type: "folder", name: "frontend/", depth: 1, empty: true },
  { type: "folder", name: "database/", depth: 1, empty: true },
  { type: "folder", name: "embeddings/", depth: 1, empty: true },
  { type: "folder", name: "docker/", depth: 1, empty: true },
  { type: "folder", name: "docs/", depth: 1, empty: true },
  { type: "folder", name: "uploads/", depth: 1, empty: true },
];
