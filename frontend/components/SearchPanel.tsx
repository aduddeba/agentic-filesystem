"use client";

import { useRef, useState, type ChangeEvent, type ReactNode } from "react";
import { searchFiles } from "../lib/api";
import type { SearchEntry } from "../lib/types";

interface Props {
  hidden: boolean;
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

export default function SearchPanel({ hidden, totalFiles, onLogSearch, onResultClick }: Props) {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<SearchEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  function runSearch(value: string) {
    const q = value.trim();
    if (!q) {
      setMatches([]);
      setSearched(false);
      return;
    }

    const id = ++requestId.current;
    setLoading(true);
    searchFiles(q)
      .then((results) => {
        if (id !== requestId.current) return;
        setMatches(results);
        setSearched(true);
        onLogSearch(q, results.length);
      })
      .catch(() => {
        if (id !== requestId.current) return;
        setMatches([]);
        setSearched(true);
      })
      .finally(() => {
        if (id === requestId.current) setLoading(false);
      });
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setQuery(value);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSearch(value), 400);
  }

  const q = query.trim();
  const fileCount = new Set(matches.map((m) => m.file)).size;

  return (
    <div id="panelSearch" style={{ display: hidden ? "none" : "flex" }}>
      <div className="search-box">
        <input type="text" value={query} onChange={handleChange} placeholder="Search file contents…" autoComplete="off" />
        <div className="search-note">Searches file contents under storage/ via the backend search API.</div>
      </div>

      <div className="search-meta">
        {!q
          ? "Type to search across the files in storage/."
          : loading
          ? "Searching…"
          : matches.length
          ? `${matches.length} match${matches.length === 1 ? "" : "es"} in ${fileCount} file${fileCount === 1 ? "" : "s"}`
          : `No matches for "${query}".`}
      </div>

      <div className="pane-body">
        {q && searched && !loading && !matches.length && (
          <div className="empty-state">Nothing found — storage/ has {totalFiles} file{totalFiles === 1 ? "" : "s"}.</div>
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
