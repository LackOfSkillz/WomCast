import React from 'react';
import ReactDOM from 'react-dom/client';
import { RemoteApp } from './App';
import './App.css';

async function registerServiceWorker(): Promise<void> {
  if ('serviceWorker' in navigator) {
    try {
      const swUrl = new URL('./service-worker.js', import.meta.url);
      const scope = new URL('./', window.location.href).pathname;
      await navigator.serviceWorker.register(swUrl, { scope });
    } catch (error) {
      console.warn('Service worker registration failed', error);
    }
  }
}

if (import.meta.env.PROD) {
  void registerServiceWorker();
}

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found for PWA remote');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <RemoteApp />
  </React.StrictMode>
);
