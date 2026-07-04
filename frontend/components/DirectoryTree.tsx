"use client";

import { TREE } from "../lib/tree";

interface Props {
  currentFile: string;
  onSelect: (path: string) => void;
}

export default function DirectoryTree({ currentFile, onSelect }: Props) {
  const fileCount = TREE.filter((node) => node.type === "file").length;

  return (
    <nav className="pane tree" aria-label="Directory">
      <div className="pane-head">
        Directory <small>{fileCount} files</small>
      </div>
      <div className="pane-body">
        <ul>
          {TREE.map((node, i) => (
            <li key={i}>
              {node.type === "folder" ? (
                <div className="node folder" style={{ paddingLeft: node.depth * 14 + 6 }}>
                  {node.name}
                  {node.empty && <span className="empty">(empty)</span>}
                </div>
              ) : (
                <button
                  type="button"
                  className={"node file" + (node.path === currentFile ? " active" : "")}
                  style={{ paddingLeft: node.depth * 14 + 6 }}
                  onClick={() => onSelect(node.path)}
                >
                  {node.name}
                </button>
              )}
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
