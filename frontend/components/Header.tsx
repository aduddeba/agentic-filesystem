export default function Header() {
  return (
    <header className="bar">
      <div className="brand">
        <span className="name">agentic-filesystem</span>
        <span className="tag">a workbench for the read · search · write tools</span>
      </div>
      <div className="legend">
        <span className="chip c-read">READ</span>
        <span className="chip c-search">SEARCH</span>
        <span className="chip c-write">WRITE</span>
      </div>
      <div className="meta">
        <b>aduddeba/agentic-filesystem</b> · main
      </div>
    </header>
  );
}
