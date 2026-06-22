import { create } from "zustand";

import type { ClaimSummary, DashboardEvent, DashboardTransportStatus } from "@/types";

interface DashboardState {
  claims: ClaimSummary[];
  events: DashboardEvent[];
  transportStatus: DashboardTransportStatus;
  setClaims: (claims: ClaimSummary[]) => void;
  pushEvent: (event: DashboardEvent) => void;
  setTransportState: (
    channel: keyof DashboardTransportStatus,
    state: DashboardTransportStatus[keyof DashboardTransportStatus]
  ) => void;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  claims: [],
  events: [],
  transportStatus: {
    sse: "idle",
    websocket: "idle"
  },
  setClaims: (claims) => set({ claims }),
  pushEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 20)
    })),
  setTransportState: (channel, transportState) =>
    set((state) => ({
      transportStatus: {
        ...state.transportStatus,
        [channel]: transportState
      }
    }))
}));
