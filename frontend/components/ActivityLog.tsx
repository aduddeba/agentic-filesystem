"use client";

import type { Activity } from "../lib/types";
import { relTime } from "../lib/time";

interface Props {
  activities: Activity[];
}

export default function ActivityLog({ activities }: Props) {
  return (
    <aside className="pane log" aria-label="Activity">
      <div className="pane-head">
        Activity
        <span className="live">
          <span className="live-dot" />
          <small>watching backend/</small>
        </span>
      </div>
      <div className="pane-body">
        <ul className="activity">
          {activities.map((a, i) => (
            <li key={i} data-tool={a.tool}>
              <div className="a-row">
                <span className="a-badge">{a.tool}</span>
                <span className="a-time">{relTime(a.ts)}</span>
              </div>
              <div className="a-detail">{a.detail}</div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
