import { useState } from 'react';
import './CloudBadge.css';

interface CloudService {
  provider: string;
  name: string;
  description: string;
  iconUrl: string;
  requiresSubscription: boolean;
  regions: string[];
}

interface CloudBadgeProps {
  service: CloudService;
  contentId: string;
  contentTitle: string;
  onWatchClick?: (provider: string, contentId: string) => void;
}

interface CloudLinkResponse {
  qrCodeUrl?: string | null;
  webLink?: string | null;
}

function isCloudLinkResponse(value: unknown): value is CloudLinkResponse {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  const qr = record.qrCodeUrl;
  const web = record.webLink;

  const qrValid = qr === undefined || qr === null || typeof qr === 'string';
  const webValid = web === undefined || web === null || typeof web === 'string';

  return qrValid && webValid;
}

export function CloudBadge({
  service,
  contentId,
  contentTitle,
  onWatchClick,
}: CloudBadgeProps): React.JSX.Element {
  const [showQr, setShowQr] = useState(false);
  const [qrCodeUrl, setQrCodeUrl] = useState<string | null>(null);

  const handleWatchClick = async () => {
    try {
      // Create cloud link
      const response = await fetch('/v1/cloud/links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: service.provider,
          title: contentTitle,
          contentId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create cloud link');
      }

      const parsed: unknown = await response.json();
      if (!isCloudLinkResponse(parsed)) {
        throw new Error('Unexpected response from cloud service');
      }

      // Set QR code URL
      setQrCodeUrl(parsed.qrCodeUrl ?? null);

      // Show QR modal
      setShowQr(true);

      // Callback
      onWatchClick?.(service.provider, contentId);
    } catch (error) {
      console.error('Failed to create cloud link:', error);
    }
  };

  const handleOpenWeb = async () => {
    try {
      const response = await fetch('/v1/cloud/links', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: service.provider,
          title: contentTitle,
          contentId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create cloud link');
      }

      const parsed: unknown = await response.json();
      if (!isCloudLinkResponse(parsed) || typeof parsed.webLink !== 'string') {
        throw new Error('Unexpected response from cloud service');
      }

      window.open(parsed.webLink, '_blank');
    } catch (error) {
      console.error('Failed to open web link:', error);
    }
  };

  const handleCloseQr = () => {
    setShowQr(false);
  };

  return (
    <>
      <div className="cloud-badge">
        <img
          src={service.iconUrl}
          alt={service.name}
          className="cloud-badge-icon"
        />
        <div className="cloud-badge-content">
          <div className="cloud-badge-header">
            <span className="cloud-badge-name">{service.name}</span>
            {service.requiresSubscription && (
              <span className="cloud-badge-subscription">⭐ Subscription</span>
            )}
          </div>
          <p className="cloud-badge-description">{service.description}</p>
          <div className="cloud-badge-actions">
            <button
              className="cloud-badge-button primary"
              onClick={handleWatchClick}
              type="button"
            >
              📱 Scan QR
            </button>
            <button
              className="cloud-badge-button secondary"
              onClick={handleOpenWeb}
              type="button"
            >
              🌐 Open in Browser
            </button>
          </div>
        </div>
      </div>

      {showQr && qrCodeUrl && (
        <div className="cloud-qr-modal" onClick={handleCloseQr}>
          <div
            className="cloud-qr-content"
            onClick={(e) => { e.stopPropagation(); }}
          >
            <h3>Scan to Watch on {service.name}</h3>
            <img
              src={qrCodeUrl}
              alt="QR Code"
              className="cloud-qr-image"
            />
            <p className="cloud-qr-instructions">
              Scan this code with your mobile device to open {contentTitle} in
              the {service.name} app
            </p>
            {service.requiresSubscription && (
              <p className="cloud-qr-note">
                ⭐ Active {service.name} subscription required
              </p>
            )}
            <button
              className="cloud-qr-close"
              onClick={handleCloseQr}
              type="button"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
