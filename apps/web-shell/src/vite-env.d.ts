/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WEB_SHELL_PORT?: string
  readonly VITE_WEB_ANALYSIS_REMOTE?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
