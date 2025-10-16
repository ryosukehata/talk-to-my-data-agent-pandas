/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ENABLE_TEMPLATE_EDIT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
