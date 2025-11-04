import './OfflineBanner.css';

interface OfflineBannerProps {
  online: boolean;
}

/**
 * Lightweight banner that informs users about offline mode.
 */
export function OfflineBanner({ online }: OfflineBannerProps): React.JSX.Element | null {
  if (online) {
    return null;
  }

  return (
    <div className="offline-banner" role="status" aria-live="polite">
      <span className="offline-indicator" aria-hidden="true">⚠️</span>
      <span>Connection lost. Some features are unavailable until we reconnect.</span>
    </div>
  );
}
