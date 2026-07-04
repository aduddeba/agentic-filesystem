"use client";

import { useMemo, useRef, useState } from "react";
import DirectoryTree from "./DirectoryTree";
import ContentsPanel from "./ContentsPanel";
import SearchPanel from "./SearchPanel";
import ActivityLog from "./ActivityLog";
import { FILES_INITIAL } from "../lib/files";
import { useActivityLog } from "../hooks/useActivityLog";
import type { SearchEntry } from "../lib/types";

const DEFAULT_FILE = "backend/tools/filesystem/search.py";

interface ScrollRequest {
  line: number;
  token: number;
}

export default function WorkbenchBody() {
  const [files, setFiles] = useState<Record<string, string>>(() => ({ ...FILES_INITIAL }));
  const [currentFile, setCurrentFile] = useState(DEFAULT_FILE);
  const [tab, setTab] = useState<"contents" | "search">("contents");
  const [scrollRequest, setScrollRequest] = useState<ScrollRequest | null>(null);
  const lastRead = useRef<{ path: string | null; ts: number }>({ path: DEFAULT_FILE, ts: Date.now() });
  const { activities, log } = useActivityLog();

  const searchIndex = useMemo<SearchEntry[]>(() => {
    const index: SearchEntry[] = [];
    Object.keys(files).forEach((path) => {
      files[path].split("\n").forEach((text, i) => {
        if (text.trim().length) index.push({ file: path, line: i + 1, text });
      });
    });
    return index;
  }, [files]);

  function selectFile(path: string, opts: { log?: boolean; scrollToLine?: number } = {}) {
    setCurrentFile(path);
    setTab("contents");

    if (opts.log !== false) {
      const now = Date.now();
      if (lastRead.current.path !== path || now - lastRead.current.ts > 3000) {
        log("READ", path);
        lastRead.current = { path, ts: now };
      }
    }

    setScrollRequest(opts.scrollToLine ? { line: opts.scrollToLine, token: Date.now() } : null);
  }

  function handleSave(newContent: string) {
    setFiles((prev) => ({ ...prev, [currentFile]: newContent }));
    log("WRITE", currentFile);
  }

  function handleResultClick(path: string, line: number) {
    selectFile(path, { scrollToLine: line });
  }

  return (
    <main className="workbench">
      <DirectoryTree currentFile={currentFile} onSelect={(path) => selectFile(path)} />

      <section className="pane stage">
        <div className="tabs" role="tablist">
          <button type="button" className="tab" role="tab" aria-selected={tab === "contents"} onClick={() => setTab("contents")}>
            Contents
          </button>
          <button type="button" className="tab" role="tab" aria-selected={tab === "search"} onClick={() => setTab("search")}>
            Search
          </button>
        </div>

        <ContentsPanel
          key={currentFile}
          path={currentFile}
          content={files[currentFile]}
          onSave={handleSave}
          scrollRequest={scrollRequest}
          hidden={tab !== "contents"}
        />

        <SearchPanel
          hidden={tab !== "search"}
          searchIndex={searchIndex}
          totalFiles={Object.keys(files).length}
          onLogSearch={(query, count) => log("SEARCH", `"${query}" → ${count} match${count === 1 ? "" : "es"}`)}
          onResultClick={handleResultClick}
        />
      </section>

      <ActivityLog activities={activities} />
    </main>
  );
}
