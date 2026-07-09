"use client";

import type { TreeNode } from "../lib/types";

interface Props {
  tree: TreeNode[];
  currentFile: string | null;
  loading: boolean;
  fileCount: number;
  storageRoot: string | null;
  onSelect: (path: string) => void;
  onCreateFile: () => void;
  onCreateFolder: () => void;
  onDelete: (path: string, isDir: boolean) => void;
  onReindex: () => void;
  onChangeStorageRoot: () => void;
}

export default function DirectoryTree({
  tree,
  currentFile,
  loading,
  fileCount,
  storageRoot,
  onSelect,
  onCreateFile,
  onCreateFolder,
  onDelete,
  onReindex,
  onChangeStorageRoot,
}: Props) {
  return (
    <nav className="pane tree" aria-label="Directory">
      <div className="pane-head">
        Directory <small>{fileCount} files</small>
      </div>
      {storageRoot && (
        <button
          type="button"
          className="folder-path"
          onClick={onChangeStorageRoot}
          title={`${storageRoot} — click to change`}
        >
          {storageRoot}
        </button>
      )}
      <div className="tree-toolbar">
        <button type="button" className="btn" onClick={onCreateFile}>
          + File
        </button>
        <button type="button" className="btn" onClick={onCreateFolder}>
          + Folder
        </button>
        <button type="button" className="btn" onClick={onReindex} title="Re-embed all files for semantic search">
          Reindex
        </button>
      </div>
      <div className="pane-body">
        {loading && <div className="empty-state">Loading…</div>}
        {!loading && tree.length === 0 && <div className="empty-state">storage/ is empty — create a file to start.</div>}
        <ul>
          {tree.map((node) => (
            <li key={node.path} className="node-row">
              {node.type === "folder" ? (
                <div className="node folder" style={{ paddingLeft: node.depth * 14 + 6 }}>
                  {node.name}
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
              <button
                type="button"
                className="node-delete"
                aria-label={`Delete ${node.path}`}
                onClick={() => onDelete(node.path, node.type === "folder")}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}
