"use client";

import { useCallback, useEffect, useState } from "react";
import type { Activity, Tool } from "../lib/types";

function seedActivities(): Activity[] {
  const now = Date.now();
  return [
    { tool: "READ", detail: "backend/tests/test_search.py", ts: now - (9 * 60 + 14) * 1000 },
    { tool: "SEARCH", detail: '"TODO" → 0 matches', ts: now - (6 * 60 + 2) * 1000 },
    { tool: "WRITE", detail: ".gitignore", ts: now - (4 * 60 + 30) * 1000 },
    { tool: "READ", detail: "backend/tools/filesystem/read.py", ts: now - (2 * 60 + 5) * 1000 },
    { tool: "SEARCH", detail: '"def " → 8 matches', ts: now - 41 * 1000 },
    { tool: "READ", detail: "backend/tools/filesystem/write.py", ts: now - 12 * 1000 },
  ];
}

// Seeded here with real Date.now()-based timestamps, so this hook must only
// ever run in a client-only render (see the dynamic ssr:false import of
// WorkbenchBody in app/page.tsx) -- otherwise the server-rendered and
// hydrated relative times would mismatch.
export function useActivityLog() {
  const [activities, setActivities] = useState<Activity[]>(seedActivities);
  const [, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 15000);
    return () => clearInterval(id);
  }, []);

  const log = useCallback((tool: Tool, detail: string) => {
    setActivities((prev) => [{ tool, detail, ts: Date.now() }, ...prev].slice(0, 60));
  }, []);

  const sorted = [...activities].sort((a, b) => b.ts - a.ts);
  return { activities: sorted, log };
}
