import { create } from "zustand";

interface ViewState {
  focusedWidgetId: string | null;
  selectedClaimId: number | null;
  focusWidget: (widgetId: string | null) => void;
  selectClaim: (claimId: number | null) => void;
}

export const useViewStore = create<ViewState>((set) => ({
  focusedWidgetId: "portfolio-overview",
  selectedClaimId: null,
  focusWidget: (focusedWidgetId) => set({ focusedWidgetId }),
  selectClaim: (selectedClaimId) => set({ selectedClaimId })
}));
