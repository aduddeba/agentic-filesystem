"use client";

import { useMemo, useRef, useState, type ChangeEvent, type ReactNode } from "react";
import type { SearchEntry } from "../lib/types";

interface Props {
  hidden: boolean;
  searchIndex: SearchEntry[];
  totalFiles: number;
  onLogSearch: (query: string, count: number) => void;
  onResultClick: (file: string, line: number) => void;
}

function highlightMatch(text: string, query: string): ReactNode[] {
  const q = query.trim();
  if (!q) return [text];
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`(${escaped})`, "ig");
  const parts = text.split(re);
  return parts.map((part, i) => (part.toLowerCase() === q.toLowerCase() ? <mark key={i}>{part}</mark> : part));
}

export default function SearchPanel({ hidden, searchIndex, totalFiles, onLogSearch, onResultClick }: Props) {
  const [query, setQuery] = useState("def ");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    return searchIndex.filter((entry) => entry.text.toLowerCase().includes(q));
  }, [query, searchIndex]);

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setQuery(value);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const q = value.trim();
      if (!q) return;
      const qLower = q.toLowerCase();
      const count = searchIndex.filter((entry) => entry.text.toLowerCase().includes(qLower)).length;
      onLogSearch(q, count);
    }, 500);
  }

  const q = query.trim();
  const fileCount = new Set(matches.map((m) => m.file)).size;

  return (
    <div id="panelSearch" style={{ display: hidden ? "none" : "flex" }}>
      <div className="search-box">
        <input type="text" value={query} onChange={handleChange} placeholder="Search file contents…" autoComplete="off" />
        <div className="search-note">
          Searches the contents of the files in this workbench, same substring match the python fallback in{" "}
          <b style={{ color: "var(--ink-soft)" }}>search.py</b> uses.
        </div>
      </div>

      <div className="search-meta">
        {!q
          ? "Type to search across the files in this workbench."
          : matches.length
          ? `${matches.length} match${matches.length === 1 ? "" : "es"} in ${fileCount} file${fileCount === 1 ? "" : "s"}`
          : `No matches for "${query}".`}
      </div>

      <div className="pane-body">
        {q && !matches.length && (
          <div className="empty-state">Nothing found — the workbench only indexes the {totalFiles} files shown in Directory.</div>
        )}
        {matches.slice(0, 200).map((m, idx) => {
          const short = m.file.split("/").slice(-1)[0];
          return (
            <button
              key={`${m.file}:${m.line}:${idx}`}
              type="button"
              className="result"
              onClick={() => onResultClick(m.file, m.line)}
            >
              <div className="rfile">
                <b>{short}</b> · {m.file}:{m.line}
              </div>
              <div className="rtext">{highlightMatch(m.text, query)}</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
