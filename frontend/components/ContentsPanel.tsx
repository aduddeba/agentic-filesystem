"use client";

import { useEffect, useRef, useState } from "react";
import { tokenizePythonLine } from "../lib/highlight";

interface ScrollRequest {
  line: number;
  token: number;
}

interface Props {
  path: string;
  content: string;
  onSave: (newContent: string) => void;
  scrollRequest: ScrollRequest | null;
  hidden: boolean;
}

// Mounted fresh per file via a `key={path}` prop from the parent, so editing
// state, the draft buffer, and the "Saved" flag all reset automatically
// whenever the selected file changes -- no manual reset logic needed.
export default function ContentsPanel({ path, content, onSave, scrollRequest, hidden }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(content);
  const [savedVisible, setSavedVisible] = useState(false);
  const [flashLine, setFlashLine] = useState<number | null>(null);
  const viewRef = useRef<HTMLDivElement | null>(null);
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const lines = content.split("\n");
  const segs = path.split("/");
  const dir = segs.slice(0, -1).join("/") + "/";
  const file = segs[segs.length - 1];

  useEffect(() => {
    if (!scrollRequest) return;
    const el = viewRef.current?.querySelector(`[data-line="${scrollRequest.line}"]`);
    if (!el) return;
    el.scrollIntoView({ block: "center" });
    setFlashLine(scrollRequest.line);
    if (flashTimer.current) clearTimeout(flashTimer.current);
    flashTimer.current = setTimeout(() => setFlashLine(null), 1400);
  }, [scrollRequest]);

  useEffect(
    () => () => {
      if (savedTimer.current) clearTimeout(savedTimer.current);
      if (flashTimer.current) clearTimeout(flashTimer.current);
    },
    []
  );

  function startEdit() {
    setDraft(content);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
  }

  function saveEdit() {
    onSave(draft);
    setEditing(false);
    setSavedVisible(true);
    if (savedTimer.current) clearTimeout(savedTimer.current);
    savedTimer.current = setTimeout(() => setSavedVisible(false), 1800);
  }

  return (
    <div id="panelContents" style={{ display: hidden ? "none" : "flex" }}>
      <div className="toolbar">
        <div className="breadcrumb">
          <span>{dir}</span>
          <span className="file">{file}</span>
        </div>
        <div className="actions">
          <span className={"saved-flag" + (savedVisible ? " show" : "")}>Saved</span>
          {!editing && (
            <button type="button" className="btn" onClick={startEdit}>
              Edit
            </button>
          )}
          {editing && (
            <>
              <button type="button" className="btn" onClick={cancelEdit}>
                Cancel
              </button>
              <button type="button" className="btn primary" onClick={saveEdit}>
                Save
              </button>
            </>
          )}
        </div>
      </div>

      <div className="pane-body">
        {editing ? (
          <textarea
            id="codeEdit"
            style={{ display: "block" }}
            spellCheck={false}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoFocus
          />
        ) : (
          <div id="codeView" ref={viewRef}>
            {lines.map((line, i) => (
              <div key={i} className={"line" + (flashLine === i + 1 ? " flash" : "")} data-line={i + 1}>
                <span className="ln">{i + 1}</span>
                <span className="code">
                  {tokenizePythonLine(line).map((tok, ti) =>
                    tok.type === "text" ? (
                      tok.value
                    ) : (
                      <span
                        key={ti}
                        className={tok.type === "comment" ? "tok-cm" : tok.type === "string" ? "tok-str" : "tok-kw"}
                      >
                        {tok.value}
                      </span>
                    )
                  )}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="statusbar">
        <span>{lines.length} lines</span>
        <span>UTF-8 · {editing ? "editing" : "read"}</span>
      </div>
    </div>
  );
}
