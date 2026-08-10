export const runtimeConfig = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.PROD ? "" : "http://127.0.0.1:8000"),
  sseUrl: import.meta.env.VITE_SSE_URL ?? "",
  websocketUrl: import.meta.env.VITE_WEBSOCKET_URL ?? ""
};
