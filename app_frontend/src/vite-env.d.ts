/// <reference types="vite/client" />

declare module "react-syntax-highlighter" {
  interface SyntaxHighlighterProps {
    children?: import("react").ReactNode;
    className?: string;
    customStyle?: import("react").CSSProperties;
    language?: string;
    PreTag?: string;
    showLineNumbers?: boolean;
    style?: Record<string, unknown>;
    wrapLongLines?: boolean;
    wrapLines?: boolean;
  }

  export const Prism: import("react").ComponentType<SyntaxHighlighterProps>;
}

declare module "react-syntax-highlighter/dist/esm/styles/prism" {
  export const oneDark: Record<string, unknown>;
  export const oneLight: Record<string, unknown>;
}

interface ImportMetaEnv {
  readonly VITE_ENABLE_TEMPLATE_EDIT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
