import React from 'react';
import type { Settings } from '../../../types/settings';
import {
  deleteCastSession,
  getCastSessions,
  resetCastSessions,
  type CastSessionInfo,
} from '../../../services/api';

interface PairingTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
}

interface NormalizedCastSession extends CastSessionInfo {
  session_id: string;
  device_name: string;
  expires_at?: string | null;
}

const PairingTab: React.FC<PairingTabProps> = ({ settings, updateSetting, disabled }) => {
  const [pairedDevices, setPairedDevices] = React.useState<NormalizedCastSession[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [resetting, setResetting] = React.useState(false);

  const loadPairedDevices = React.useCallback(async () => {
    try {
      setLoading(true);
      const data = await getCastSessions();
      const sessions: NormalizedCastSession[] = (data.sessions ?? []).map(
        (session: CastSessionInfo): NormalizedCastSession => {
          const rawId = session.session_id ?? session.id;
          const sessionId = rawId !== undefined && rawId !== null ? String(rawId) : '';
          const deviceInfo = session.device_info ?? {};
          const resolvedName =
            (typeof session.device_name === 'string' && session.device_name.trim().length > 0
              ? session.device_name
              : undefined) ??
            (typeof deviceInfo.name === 'string' && deviceInfo.name.trim().length > 0
              ? deviceInfo.name
              : undefined) ??
            (typeof deviceInfo.device_name === 'string' && deviceInfo.device_name.trim().length > 0
              ? deviceInfo.device_name
              : undefined) ??
            'Unknown Device';

          return {
            ...session,
            session_id: sessionId,
            device_name: resolvedName,
            expires_at: session.expires_at ?? null,
          } satisfies NormalizedCastSession;
        },
      );

      setPairedDevices(sessions.filter((session) => session.session_id.length > 0));
    } catch (error) {
      console.error('Failed to load paired devices:', error);
      setPairedDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadPairedDevices();
  }, [loadPairedDevices]);

  const removePairing = async (sessionId: string) => {
    if (disabled) {
      return;
    }

    if (!confirm('Remove this pairing? The device will need to re-pair to cast again.')) {
      return;
    }

    try {
      await deleteCastSession(sessionId);
      await loadPairedDevices();
    } catch (error) {
      console.error('Failed to remove pairing:', error);
      alert('Failed to remove pairing. Please try again.');
    }
  };

  const resetPairings = async () => {
    if (disabled) {
      return;
    }

    if (!confirm('Reset all cast pairings? All devices will need to pair again.')) {
      return;
    }

    try {
      setResetting(true);
      const data = await resetCastSessions();
      await loadPairedDevices();
      alert(data.message || 'All pairings have been reset.');
    } catch (error) {
      console.error('Failed to reset pairings:', error);
      alert('Failed to reset pairings. Please try again.');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="settings-tab">
      {/* Pairing Configuration */}
      <div className="settings-section">
        <h2>📱 Pairing Configuration</h2>
        <p className="description">
          Configure how devices pair with WomCast for casting.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Enable Pairing</h3>
            <p>Allow new devices to pair with WomCast</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.pairing_enabled !== false}
                onChange={(e) => updateSetting('pairing_enabled', e.target.checked)}
                disabled={disabled}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>PIN Length</h3>
            <p>Number of digits in pairing PINs</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={settings.pairing_pin_length || 6}
              onChange={(e) => updateSetting('pairing_pin_length', parseInt(e.target.value, 10))}
              disabled={disabled}
            >
              <option value="4">4 digits</option>
              <option value="6">6 digits</option>
              <option value="8">8 digits</option>
            </select>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Session Timeout</h3>
            <p>How long pairing sessions remain valid</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={settings.pairing_session_timeout || 300}
              onChange={(e) => updateSetting('pairing_session_timeout', parseInt(e.target.value, 10))}
              disabled={disabled}
            >
              <option value="60">1 minute</option>
              <option value="300">5 minutes</option>
              <option value="600">10 minutes</option>
              <option value="1800">30 minutes</option>
              <option value="3600">1 hour</option>
            </select>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Reset Pairings</h3>
            <p>Clear all active cast sessions and paired devices</p>
          </div>
          <div className="settings-control">
            <button
              className="settings-button secondary"
              onClick={resetPairings}
              disabled={resetting || disabled}
            >
              {resetting ? 'Resetting...' : 'Reset All Pairings'}
            </button>
          </div>
        </div>
      </div>

      {/* Paired Devices */}
      <div className="settings-section">
        <h2>🔗 Paired Devices</h2>
        <p className="description">
          Manage devices that have paired with WomCast. Remove pairings to require devices to re-authenticate.
        </p>
        
        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#aaa' }}>
            Loading paired devices...
          </div>
        ) : pairedDevices.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#aaa' }}>
            No devices paired yet.
          </div>
        ) : (
          <ul className="settings-list">
            {pairedDevices.map((device) => (
              <li key={device.session_id} className="settings-list-item">
                <div className="settings-list-item-info">
                  <h4>{device.device_name || 'Unknown Device'}</h4>
                  <p>
                    Session ID: {device.session_id.substring(0, 12)}...
                    {device.expires_at && ` • Expires: ${new Date(device.expires_at).toLocaleString()}`}
                  </p>
                </div>
                <div className="settings-list-item-actions">
                  <button 
                    className="settings-button secondary"
                    onClick={() => removePairing(device.session_id)}
                    disabled={disabled}
                  >
                    Remove
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default PairingTab;
