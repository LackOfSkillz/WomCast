/**
 * Cast Pairing View - QR code display for phone/tablet pairing
 */

import { useState, useEffect } from 'react';
import './CastView.css';

interface Session {
  session_id: string;
  pin: string;
  qr_data: string;
  expires_in_seconds: number;
}

const CastView = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [qrImageUrl, setQrImageUrl] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number>(0);

  const createSession = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('http://localhost:3005/v1/cast/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ device_type: 'phone' }),
      });

      if (!response.ok) {
        throw new Error('Failed to create session');
      }

      const data: Session = await response.json();
      setSession(data);
      setExpiresIn(data.expires_in_seconds);

      // Fetch QR code image
      const qrResponse = await fetch(
        `http://localhost:3005/v1/cast/session/${data.session_id}/qr`
      );
      if (qrResponse.ok) {
        const blob = await qrResponse.blob();
        const url = URL.createObjectURL(blob);
        setQrImageUrl(url);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

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
    };
  }, [qrImageUrl]);

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

      {!session && !loading && (
        <button onClick={createSession} className="create-session-btn">
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
              createSession();
            }}
            className="refresh-btn"
          >
            Generate New Code
          </button>
        </div>
      )}
    </div>
  );
};

export default CastView;
