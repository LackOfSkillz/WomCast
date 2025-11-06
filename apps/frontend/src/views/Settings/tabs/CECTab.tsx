import React from 'react';
import type { Settings } from '../../../types/settings';

interface CECDevice {
  address: string;
  name: string | null;
  vendor: string | null;
  active: boolean;
}

function isCECDevice(value: unknown): value is CECDevice {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const record = value as Record<string, unknown>;
  return (
    typeof record.address === 'string' &&
    (typeof record.name === 'string' || record.name === null || record.name === undefined) &&
    (typeof record.vendor === 'string' || record.vendor === null || record.vendor === undefined) &&
    typeof record.active === 'boolean'
  );
}

interface CECTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
}

const CECTab: React.FC<CECTabProps> = ({ settings, updateSetting, disabled }) => {
  const [devices, setDevices] = React.useState<CECDevice[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [scanning, setScanning] = React.useState(false);

  React.useEffect(() => {
    void loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/cast/v1/cec/devices');
      const payload: unknown = await response.json();
      let deviceList: CECDevice[] = [];

      if (typeof payload === 'object' && payload !== null) {
        const maybeDevices = (payload as { devices?: unknown }).devices;
        if (Array.isArray(maybeDevices)) {
          deviceList = maybeDevices.filter(isCECDevice);
        }
      }

      setDevices(deviceList);
    } catch (error) {
      console.error('Failed to load CEC devices:', error);
    } finally {
      setLoading(false);
    }
  };

  const scanDevices = async () => {
    if (disabled || !settings.cec_enabled) {
      return;
    }

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
    if (disabled) {
      return;
    }

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
                disabled={disabled}
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
                disabled={!settings.cec_enabled || disabled}
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
            disabled={scanning || !settings.cec_enabled || disabled}
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
                    disabled={device.active || disabled}
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
