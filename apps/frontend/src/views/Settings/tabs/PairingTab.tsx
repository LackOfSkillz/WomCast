import React from 'react';

interface PairingTabProps {
  settings: {
    pairing_enabled?: boolean;
    pairing_pin_length?: number;
    pairing_session_timeout?: number;
  };
  updateSetting: (key: string, value: any) => Promise<void>;
  updateSettings: (updates: any) => Promise<void>;
}

const PairingTab: React.FC<PairingTabProps> = ({ settings, updateSetting }) => {
  const [pairedDevices, setPairedDevices] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    loadPairedDevices();
  }, []);

  const loadPairedDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/cast/v1/sessions');
      const data = await response.json();
      setPairedDevices(data.sessions || []);
    } catch (error) {
      console.error('Failed to load paired devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const removePairing = async (sessionId: string) => {
    if (!confirm('Remove this pairing? The device will need to re-pair to cast again.')) {
      return;
    }

    try {
      await fetch(`/api/cast/v1/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      await loadPairedDevices();
    } catch (error) {
      console.error('Failed to remove pairing:', error);
      alert('Failed to remove pairing. Please try again.');
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
              onChange={(e) => updateSetting('pairing_pin_length', parseInt(e.target.value))}
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
              onChange={(e) => updateSetting('pairing_session_timeout', parseInt(e.target.value))}
            >
              <option value="60">1 minute</option>
              <option value="300">5 minutes</option>
              <option value="600">10 minutes</option>
              <option value="1800">30 minutes</option>
              <option value="3600">1 hour</option>
            </select>
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
