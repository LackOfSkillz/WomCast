import React from 'react';

interface CECDevice {
  address: string;
  name: string;
  vendor: string;
  active: boolean;
}

interface CECTabProps {
  settings: {
    cec_enabled?: boolean;
    cec_auto_switch?: boolean;
  };
  updateSetting: (key: string, value: any) => Promise<void>;
  updateSettings: (updates: any) => Promise<void>;
}

const CECTab: React.FC<CECTabProps> = ({ settings, updateSetting }) => {
  const [devices, setDevices] = React.useState<CECDevice[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [scanning, setScanning] = React.useState(false);

  React.useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/cast/v1/cec/devices');
      const data = await response.json();
      setDevices(data.devices || []);
    } catch (error) {
      console.error('Failed to load CEC devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const scanDevices = async () => {
    try {
      setScanning(true);
      await fetch('/api/cast/v1/cec/scan', { method: 'POST' });
      await loadDevices();
    } catch (error) {
      console.error('Failed to scan CEC devices:', error);
      alert('Failed to scan for devices. Please try again.');
    } finally {
      setScanning(false);
    }
  };

  const switchToInput = async (address: string) => {
    try {
      await fetch('/api/cast/v1/cec/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
    } catch (error) {
      console.error('Failed to switch input:', error);
      alert('Failed to switch input. Please try again.');
    }
  };

  return (
    <div className="settings-tab">
      {/* CEC Configuration */}
      <div className="settings-section">
        <h2>📺 HDMI-CEC Configuration</h2>
        <p className="description">
          Control your TV and other HDMI devices using the CEC protocol. Requires CEC-enabled HDMI hardware.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Enable CEC</h3>
            <p>Enable HDMI-CEC device control</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.cec_enabled === true}
                onChange={(e) => updateSetting('cec_enabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Auto-Switch Input</h3>
            <p>Automatically switch TV input when starting playback</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.cec_auto_switch === true}
                onChange={(e) => updateSetting('cec_auto_switch', e.target.checked)}
                disabled={!settings.cec_enabled}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* CEC Devices */}
      <div className="settings-section">
        <h2>🔌 HDMI Devices</h2>
        <p className="description">
          Detected HDMI-CEC devices on the bus. Click a device to switch to its input.
        </p>
        
        <div style={{ marginBottom: '1rem' }}>
          <button 
            className="settings-button"
            onClick={scanDevices}
            disabled={scanning || !settings.cec_enabled}
          >
            {scanning ? 'Scanning...' : '🔍 Scan for Devices'}
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#aaa' }}>
            Loading devices...
          </div>
        ) : !settings.cec_enabled ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#aaa' }}>
            Enable CEC to see devices.
          </div>
        ) : devices.length === 0 ? (
          <div style={{ padding: '2rem', textAlign: 'center', color: '#aaa' }}>
            No CEC devices found. Try scanning.
          </div>
        ) : (
          <ul className="settings-list">
            {devices.map((device) => (
              <li key={device.address} className="settings-list-item">
                <div className="settings-list-item-info">
                  <h4>
                    {device.name || 'Unknown Device'}
                    {device.active && ' ⭐ Active'}
                  </h4>
                  <p>
                    Address: {device.address}
                    {device.vendor && ` • Vendor: ${device.vendor}`}
                  </p>
                </div>
                <div className="settings-list-item-actions">
                  <button 
                    className="settings-button"
                    onClick={() => switchToInput(device.address)}
                    disabled={device.active}
                  >
                    {device.active ? 'Current' : 'Switch To'}
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

export default CECTab;
