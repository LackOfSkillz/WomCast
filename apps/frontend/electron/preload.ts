// Preload script for Electron renderer process
// Exposes safe APIs to the renderer via contextBridge

import { contextBridge } from 'electron';

// Expose APIs to renderer
contextBridge.exposeInMainWorld('electron', {
  platform: process.platform,
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
