"use client";

import { useRef, useState, type ChangeEvent, type ReactNode } from "react";
import { searchFiles, searchSemantic } from "../lib/api";
import type { SearchEntry, SemanticEntry } from "../lib/types";

type Mode = "keyword" | "semantic";

interface Props {
  hidden: boolean;
  totalFiles: number;
  onLogSearch: (query: string, count: number) => void;
  onResultClick: (file: string, line: number) => void;
  onSemanticResultClick: (file: string) => void;
}

function highlightMatch(text: string, query: string): ReactNode[] {
  const q = query.trim();
  if (!q) return [text];
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp(`(${escaped})`, "ig");
  const parts = text.split(re);
  return parts.map((part, i) => (part.toLowerCase() === q.toLowerCase() ? <mark key={i}>{part}</mark> : part));
}

export default function SearchPanel({ hidden, totalFiles, onLogSearch, onResultClick, onSemanticResultClick }: Props) {
  const [mode, setMode] = useState<Mode>("keyword");
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<SearchEntry[]>([]);
  const [semanticMatches, setSemanticMatches] = useState<SemanticEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestId = useRef(0);

  function runSearch(value: string, activeMode: Mode) {
    const q = value.trim();
    if (!q) {
      setMatches([]);
      setSemanticMatches([]);
      setSearched(false);
      return;
    }

    const id = ++requestId.current;
    setLoading(true);
    const request =
      activeMode === "keyword"
        ? searchFiles(q).then((results) => {
            setMatches(results);
            setSemanticMatches([]);
            return results.length;
          })
        : searchSemantic(q).then((results) => {
            setSemanticMatches(results);
            setMatches([]);
            return results.length;
          });

    request
      .then((count) => {
        if (id !== requestId.current) return;
        setSearched(true);
        onLogSearch(q, count);
      })
      .catch(() => {
        if (id !== requestId.current) return;
        setMatches([]);
        setSemanticMatches([]);
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
    debounceRef.current = setTimeout(() => runSearch(value, mode), 400);
  }

  function handleModeChange(next: Mode) {
    if (next === mode) return;
    setMode(next);
    if (query.trim()) runSearch(query, next);
  }

  const q = query.trim();
  const resultCount = mode === "keyword" ? matches.length : semanticMatches.length;
  const fileCount =
    mode === "keyword" ? new Set(matches.map((m) => m.file)).size : new Set(semanticMatches.map((m) => m.file)).size;

  return (
    <div id="panelSearch" style={{ display: hidden ? "none" : "flex" }}>
      <div className="search-mode">
        <button
          type="button"
          className="btn"
          aria-pressed={mode === "keyword"}
          onClick={() => handleModeChange("keyword")}
        >
          Keyword
        </button>
        <button
          type="button"
          className="btn"
          aria-pressed={mode === "semantic"}
          onClick={() => handleModeChange("semantic")}
        >
          Semantic
        </button>
      </div>

      <div className="search-box">
        <input
          type="text"
          value={query}
          onChange={handleChange}
          placeholder={mode === "keyword" ? "Search file contents…" : "Describe what you're looking for…"}
          autoComplete="off"
        />
        <div className="search-note">
          {mode === "keyword"
            ? "Searches file contents under storage/ via the backend search API."
            : "Finds files by meaning, not just exact words, blending vector and keyword search."}
        </div>
      </div>

      <div className="search-meta">
        {!q
          ? "Type to search across the files in storage/."
          : loading
          ? "Searching…"
          : resultCount
          ? `${resultCount} match${resultCount === 1 ? "" : "es"} in ${fileCount} file${fileCount === 1 ? "" : "s"}`
          : `No matches for "${query}".`}
      </div>

      <div className="pane-body">
        {q && searched && !loading && !resultCount && (
          <div className="empty-state">Nothing found — storage/ has {totalFiles} file{totalFiles === 1 ? "" : "s"}.</div>
        )}
        {mode === "keyword"
          ? matches.slice(0, 200).map((m, idx) => {
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
            })
          : semanticMatches.slice(0, 200).map((m, idx) => {
              const short = m.file.split("/").slice(-1)[0];
              return (
                <button
                  key={`${m.file}:${idx}`}
                  type="button"
                  className="result"
                  onClick={() => onSemanticResultClick(m.file)}
                >
                  <div className="rfile">
                    <b>{short}</b> · {m.file}
                    <span className="rscore">{m.score.toFixed(2)}</span>
                  </div>
                  <div className="rtext">{m.text}</div>
                </button>
              );
            })}
      </div>
    </div>
  );
}
