import { create } from "zustand";

import type { ClaimDocumentResponse, ClaimResponse } from "../types/api";

type ActivityEntry = {
  id: string;
  message: string;
  createdAt: string;
};

type ClaimIntakeState = {
  claim: ClaimResponse | null;
  queue: ClaimDocumentResponse[];
  activityLog: ActivityEntry[];
  isUploading: boolean;
  uploadProgress: Record<string, number>;
  setClaim: (claim: ClaimResponse | null) => void;
  setQueue: (queue: ClaimDocumentResponse[]) => void;
  updateQueueDocument: (document: ClaimDocumentResponse) => void;
  setUploading: (value: boolean) => void;
  setUploadProgress: (fileName: string, progress: number) => void;
  clearUploadProgress: (fileName: string) => void;
  addLog: (message: string) => void;
  reset: () => void;
};

export const useClaimIntakeStore = create<ClaimIntakeState>((set) => ({
  claim: null,
  queue: [],
  activityLog: [],
  isUploading: false,
  uploadProgress: {},
  setClaim: (claim) => set({ claim }),
  setQueue: (queue) => set({ queue }),
  updateQueueDocument: (document) =>
    set((state) => ({
      queue: state.queue.some((item) => item.id === document.id)
        ? state.queue.map((item) => (item.id === document.id ? document : item))
        : [...state.queue, document]
    })),
  setUploading: (value) => set({ isUploading: value }),
  setUploadProgress: (fileName, progress) =>
    set((state) => ({
      uploadProgress: {
        ...state.uploadProgress,
        [fileName]: progress
      }
    })),
  clearUploadProgress: (fileName) =>
    set((state) => {
      const next = { ...state.uploadProgress };
      delete next[fileName];
      return { uploadProgress: next };
    }),
  addLog: (message) =>
    set((state) => ({
      activityLog: [
        {
          id: `${Date.now()}-${state.activityLog.length}`,
          message,
          createdAt: new Date().toISOString()
        },
        ...state.activityLog
      ]
    })),
  reset: () =>
    set({
      claim: null,
      queue: [],
      activityLog: [],
      isUploading: false,
      uploadProgress: {}
    })
}));
