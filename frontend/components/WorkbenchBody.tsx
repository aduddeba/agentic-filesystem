"use client";

import { useEffect, useRef, useState } from "react";
import DirectoryTree from "./DirectoryTree";
import ContentsPanel from "./ContentsPanel";
import SearchPanel from "./SearchPanel";
import ActivityLog from "./ActivityLog";
import { useActivityLog } from "../hooks/useActivityLog";
import {
  ApiError,
  createEntry,
  deleteEntry,
  fetchFileContent,
  fetchSettings,
  fetchStats,
  fetchTree,
  reindexAll,
  updateFileContent,
  updateStorageRoot,
} from "../lib/api";
import type { TreeNode } from "../lib/types";

interface ScrollRequest {
  line: number;
  token: number;
}

export default function WorkbenchBody() {
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [treeLoading, setTreeLoading] = useState(true);
  const [fileCount, setFileCount] = useState(0);
  const [currentFile, setCurrentFile] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [contentLoading, setContentLoading] = useState(false);
  const [tab, setTab] = useState<"contents" | "search">("contents");
  const [scrollRequest, setScrollRequest] = useState<ScrollRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [storageRoot, setStorageRoot] = useState<string | null>(null);
  const lastRead = useRef<{ path: string | null; ts: number }>({ path: null, ts: 0 });
  const { activities, log } = useActivityLog();

  function refreshStats() {
    fetchStats()
      .then((s) => setFileCount(s.file_count))
      .catch(() => {});
  }

  function refreshTree() {
    return fetchTree().then((nodes) => {
      setTree(nodes);
      return nodes;
    });
  }

  useEffect(() => {
    setError(null);
    setTreeLoading(true);
    fetchSettings()
      .then((s) => setStorageRoot(s.storage_root))
      .catch(() => {});
    refreshTree()
      .then((nodes) => {
        refreshStats();
        const firstFile = nodes.find((n) => n.type === "file");
        if (firstFile) selectFile(firstFile.path, { log: false });
      })
      .catch(() => setError("Could not reach the backend API. Is it running on NEXT_PUBLIC_API_BASE_URL?"))
      .finally(() => setTreeLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function selectFile(path: string, opts: { log?: boolean; scrollToLine?: number } = {}) {
    setCurrentFile(path);
    setTab("contents");
    setContent(null);
    setContentLoading(true);
    setError(null);

    if (opts.log !== false) {
      const now = Date.now();
      if (lastRead.current.path !== path || now - lastRead.current.ts > 3000) {
        log("READ", path);
        lastRead.current = { path, ts: now };
      }
    }

    fetchFileContent(path)
      .then((text) => {
        setContent(text);
        setScrollRequest(opts.scrollToLine ? { line: opts.scrollToLine, token: Date.now() } : null);
      })
      .catch((e) => {
        if (e instanceof ApiError && e.status === 404) {
          setError(`${path} no longer exists — it may have been deleted outside the app.`);
          setCurrentFile(null);
          setContent(null);
          refreshTree();
          refreshStats();
          return;
        }
        setError(`Failed to load ${path}`);
      })
      .finally(() => setContentLoading(false));
  }

  function handleSave(newContent: string) {
    if (!currentFile) return;
    updateFileContent(currentFile, newContent)
      .then(() => {
        setContent(newContent);
        log("WRITE", currentFile);
        refreshStats();
      })
      .catch(() => setError(`Failed to save ${currentFile}`));
  }

  function handleResultClick(path: string, line: number) {
    selectFile(path, { scrollToLine: line });
  }

  function handleSemanticResultClick(path: string) {
    selectFile(path);
  }

  function handleReindex() {
    setError(null);
    reindexAll()
      .then(({ indexed, failed }) => {
        log("REINDEX", `${indexed} indexed${failed ? `, ${failed} failed` : ""}`);
        refreshStats();
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to reindex"));
  }

  function handleChangeStorageRoot() {
    const input = window.prompt("Storage folder (absolute path):", storageRoot ?? "");
    if (!input?.trim() || input.trim() === storageRoot) return;
    setError(null);

    updateStorageRoot(input.trim())
      .then((s) => {
        setStorageRoot(s.storage_root);
        setCurrentFile(null);
        setContent(null);
        log("SETTINGS", `Storage root → ${s.storage_root}`);
        return refreshTree();
      })
      .then(() => refreshStats())
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to change storage folder"));
  }

  function handleCreateFile() {
    const input = window.prompt("New file path (relative to storage/):");
    if (!input?.trim()) return;
    setError(null);

    createEntry(input.trim(), "file", "")
      .then((node) => {
        log("CREATE", node.path);
        return refreshTree().then(() => node);
      })
      .then((node) => {
        refreshStats();
        selectFile(node.path);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : `Failed to create ${input}`));
  }

  function handleCreateFolder() {
    const input = window.prompt("New folder path (relative to storage/):");
    if (!input?.trim()) return;
    setError(null);

    createEntry(input.trim(), "directory")
      .then((node) => {
        log("CREATE", node.path + "/");
        return refreshTree();
      })
      .then(() => refreshStats())
      .catch((e) => setError(e instanceof ApiError ? e.message : `Failed to create ${input}`));
  }

  function handleDelete(path: string, isDir: boolean) {
    if (!window.confirm(`Delete ${path}${isDir ? " and everything inside it" : ""}?`)) return;
    setError(null);

    deleteEntry(path)
      .then(() => {
        log("DELETE", path);
        if (currentFile === path || (isDir && currentFile?.startsWith(path + "/"))) {
          setCurrentFile(null);
          setContent(null);
        }
        return refreshTree();
      })
      .then(() => refreshStats())
      .catch((e) => setError(e instanceof ApiError ? e.message : `Failed to delete ${path}`));
  }

  return (
    <main className="workbench">
      <DirectoryTree
        tree={tree}
        currentFile={currentFile}
        loading={treeLoading}
        fileCount={fileCount}
        storageRoot={storageRoot}
        onSelect={(path) => selectFile(path)}
        onCreateFile={handleCreateFile}
        onCreateFolder={handleCreateFolder}
        onDelete={handleDelete}
        onReindex={handleReindex}
        onChangeStorageRoot={handleChangeStorageRoot}
      />

      <section className="pane stage">
        <div className="tabs" role="tablist">
          <button type="button" className="tab" role="tab" aria-selected={tab === "contents"} onClick={() => setTab("contents")}>
            Contents
          </button>
          <button type="button" className="tab" role="tab" aria-selected={tab === "search"} onClick={() => setTab("search")}>
            Search
          </button>
        </div>

        {error && <div className="empty-state">{error}</div>}

        {!error && currentFile && content !== null && (
          <ContentsPanel
            key={currentFile}
            path={currentFile}
            content={content}
            onSave={handleSave}
            scrollRequest={scrollRequest}
            hidden={tab !== "contents"}
          />
        )}
        {!error && (!currentFile || content === null) && tab === "contents" && (
          <div className="empty-state">{contentLoading ? "Loading…" : "Select a file to view its contents."}</div>
        )}

        <SearchPanel
          hidden={tab !== "search"}
          totalFiles={fileCount}
          onLogSearch={(query, count) => log("SEARCH", `"${query}" → ${count} match${count === 1 ? "" : "es"}`)}
          onResultClick={handleResultClick}
          onSemanticResultClick={handleSemanticResultClick}
        />
      </section>

      <ActivityLog activities={activities} />
    </main>
  );
}
