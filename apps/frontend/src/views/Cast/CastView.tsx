/**
 * Cast Pairing View - QR code display for phone/tablet pairing
 */

import { useCallback, useEffect, useState } from 'react';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import { createCastSession, fetchCastSessionQr, fetchPwaQr, type CastSession } from '../../services/api';
import './CastView.css';

const OFFLINE_STATUS = 'Offline mode: reconnect to generate new pairing codes.';

const CastView = (): React.JSX.Element => {
  const [session, setSession] = useState<CastSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number>(0);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [remoteQrUrl, setRemoteQrUrl] = useState<string | null>(null);
  const [remoteQrStatus, setRemoteQrStatus] = useState<string | null>('');
  const { online } = useNetworkStatus();

  const createSession = useCallback(async () => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage(null);

    try {
      const data = await createCastSession();
      setSession(data);
      setExpiresIn(data.expires_in_seconds);

      try {
        const qrBlob = await fetchCastSessionQr(data.session_id);
        const url = URL.createObjectURL(qrBlob);
        setQrImageUrl(url);
      } catch (qrError) {
        setQrImageUrl(null);
        console.warn('Failed to load cast QR:', qrError);
        setStatusMessage('QR code unavailable right now. Use the PIN or retry after reconnecting.');
      }
    } catch (err) {
      setSession(null);
      setQrImageUrl(null);
      setExpiresIn(0);
      console.error('Failed to create cast session:', err);
      setError('Failed to create session. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [online]);

  const handleGenerateClick = () => {
    void createSession();
  };

  // Load PWA remote QR on mount
  useEffect(() => {
    const controller = new AbortController();

    const loadRemoteQr = async () => {
      try {
        setRemoteQrStatus('');
        const origin = typeof window !== 'undefined' ? window.location.origin : undefined;
        const blob = await fetchPwaQr(origin, controller.signal);
        const url = URL.createObjectURL(blob);
        setRemoteQrUrl((prev) => {
          if (prev) {
            URL.revokeObjectURL(prev);
          }
          return url;
        });
      } catch (error) {
        console.warn('Failed to load PWA remote QR:', error);
        setRemoteQrUrl(null);
        setRemoteQrStatus('Remote QR unavailable. Visit http://womcast.local:5173/pwa/ manually.');
      }
    };

    void loadRemoteQr();

    return () => {
      controller.abort();
    };
  }, []);

  // Countdown timer for session expiration
  useEffect(() => {
    if (expiresIn <= 0) return;

    const timer = setInterval(() => {
      setExpiresIn((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setSession(null);
          setQrImageUrl(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [expiresIn]);

  // Cleanup QR image URL on unmount
  useEffect(() => {
    return () => {
      if (qrImageUrl) {
        URL.revokeObjectURL(qrImageUrl);
      }
      if (remoteQrUrl) {
        URL.revokeObjectURL(remoteQrUrl);
      }
    };
  }, [qrImageUrl, remoteQrUrl]);

  useEffect(() => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
    } else if (statusMessage === OFFLINE_STATUS) {
      setStatusMessage(null);
    }
  }, [online, statusMessage]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="cast-view">
      <h1>Cast to WomCast</h1>
      <p className="cast-description">
        Scan the QR code with your phone or tablet to start casting
      </p>

      {statusMessage && (
        <div className="cast-status" role="status" aria-live="polite">
          {statusMessage}
        </div>
      )}

      {!session && !loading && (
        <button
          onClick={handleGenerateClick}
          className="create-session-btn"
          type="button"
          disabled={!online || loading}
        >
          Generate Pairing Code
        </button>
      )}

      {loading && <div className="loading-spinner">Creating session...</div>}

      {error && <div className="error-message">{error}</div>}

      {session && (
        <div className="session-container">
          <div className="pin-display">
            <h2>Pairing PIN</h2>
            <div className="pin-code">{session.pin}</div>
            <p className="pin-helper">
              Alternatively, enter this PIN manually in the WomCast app
            </p>
          </div>

          {qrImageUrl && (
            <div className="qr-container">
              <img src={qrImageUrl} alt="Pairing QR Code" className="qr-code" />
              <p className="qr-helper">
                Scan with your phone's camera or WomCast app
              </p>
            </div>
          )}

          <div className="session-info">
            <p className="expires-timer">
              Expires in: <strong>{formatTime(expiresIn)}</strong>
            </p>
            <p className="session-id">Session ID: {session.session_id}</p>
          </div>

          <button
            onClick={() => {
              setSession(null);
              setQrImageUrl(null);
              setExpiresIn(0);
              setStatusMessage(null);
              void createSession();
            }}
            className="refresh-btn"
            type="button"
            disabled={!online || loading}
          >
            Generate New Code
          </button>
        </div>
      )}

      <section className="pwa-section">
        <h2>Mobile Remote PWA</h2>
        <p className="pwa-description">
          Scan to open the LAN remote on your phone or tablet. Add to home screen for quick access.
        </p>
        {remoteQrUrl ? (
          <div className="pwa-qr-wrapper">
            <img src={remoteQrUrl} alt="WomCast Remote QR" className="qr-code" />
            <p className="qr-helper">Open http://womcast.local:5173/pwa/</p>
          </div>
        ) : (
          <div className="pwa-status" role="status">
            {remoteQrStatus || 'Preparing remote QR...'}
          </div>
        )}
      </section>
    </div>
  );
};

export default CastView;
