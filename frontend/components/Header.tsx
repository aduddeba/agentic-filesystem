export default function Header() {
  return (
    <header className="bar">
      <div className="brand">
        <span className="name">agentic-filesystem</span>
        <span className="tag">a file explorer for the storage/ workspace, backed by FastAPI + PostgreSQL</span>
      </div>
      <div className="legend">
        <span className="chip c-read">READ</span>
        <span className="chip c-search">SEARCH</span>
        <span className="chip c-write">WRITE</span>
        <span className="chip c-create">CREATE</span>
        <span className="chip c-delete">DELETE</span>
      </div>
      <div className="meta">
        <b>aduddeba/agentic-filesystem</b> · main
      </div>
    </header>
  );
}
