import dynamic from "next/dynamic";
import Header from "../components/Header";

// Client-only: the activity log seeds relative timestamps from Date.now(),
// which would mismatch between the server-rendered and hydrated markup if
// this rendered on the server too.
const WorkbenchBody = dynamic(() => import("../components/WorkbenchBody"), {
  ssr: false,
  loading: () => <main className="workbench workbench-loading">Loading workbench…</main>,
});

export default function Page() {
  return (
    <div className="app">
      <Header />
      <WorkbenchBody />
    </div>
  );
}
