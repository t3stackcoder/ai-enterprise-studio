/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ANALYSIS_SERVER_WS?: string
  readonly VITE_WEB_ANALYSIS_PORT?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
