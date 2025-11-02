/// <reference types="vite/client" />
/// <reference types="react" />
/// <reference types="react-dom" />

interface ImportMetaEnv {
  readonly VITE_METADATA_API_URL?: string;
  readonly VITE_PLAYBACK_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
