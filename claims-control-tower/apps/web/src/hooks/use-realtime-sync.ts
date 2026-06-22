import { useEffect } from "react";

import { runtimeConfig } from "@/config/runtime";
import { connectEventStream } from "@/lib/realtime/event-stream";
import { connectWebSocket } from "@/lib/realtime/socket";
import { useDashboardStore } from "@/store/dashboard-store";

function buildEvent(source: "sse" | "websocket", message: string) {
  return {
    id: `${source}-${crypto.randomUUID()}`,
    source,
    message,
    createdAt: new Date().toISOString()
  };
}

export function useRealtimeSync() {
  const pushEvent = useDashboardStore((state) => state.pushEvent);
  const setTransportState = useDashboardStore((state) => state.setTransportState);

  useEffect(() => {
    setTransportState("sse", runtimeConfig.sseUrl ? "connecting" : "idle");
    setTransportState("websocket", runtimeConfig.websocketUrl ? "connecting" : "idle");

    const eventSource = connectEventStream(runtimeConfig.sseUrl, {
      onOpen: () => setTransportState("sse", "connected"),
      onError: () => setTransportState("sse", "error"),
      onMessage: (event) => pushEvent(buildEvent("sse", event.data))
    });

    const socket = connectWebSocket(runtimeConfig.websocketUrl, {
      onOpen: () => setTransportState("websocket", "connected"),
      onError: () => setTransportState("websocket", "error"),
      onMessage: (event) => pushEvent(buildEvent("websocket", event.data))
    });

    return () => {
      eventSource?.close();
      socket?.close();
    };
  }, [pushEvent, setTransportState]);
}
