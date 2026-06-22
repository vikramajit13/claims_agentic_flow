import { useMemo } from "react";

import { DashboardShell } from "@/components/dashboard-shell";
import { widgetRegistry } from "@/config/widget-registry";
import { useDashboardBootstrap } from "@/hooks/use-dashboard-bootstrap";
import { useRealtimeSync } from "@/hooks/use-realtime-sync";
import { useViewStore } from "@/store/view-store";

export default function App() {
  useDashboardBootstrap();
  useRealtimeSync();

  const focusedWidgetId = useViewStore((state) => state.focusedWidgetId);
  const widgets = useMemo(() => widgetRegistry, []);

  return <DashboardShell widgets={widgets} focusedWidgetId={focusedWidgetId} />;
}
