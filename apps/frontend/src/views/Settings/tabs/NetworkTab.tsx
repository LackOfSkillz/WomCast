import React from 'react';
import type { Settings } from '../../../types/settings';

interface NetworkTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
}

const NetworkTab: React.FC<NetworkTabProps> = ({ settings, updateSetting, disabled }) => {
  const [diagnosing, setDiagnosing] = React.useState(false);
  const [diagnosticsResult, setDiagnosticsResult] = React.useState<string | null>(null);

  const runDiagnostics = async () => {
    if (disabled) {
      return;
    }

    try {
      setDiagnosing(true);
      setDiagnosticsResult(null);
      
      const response = await fetch('/api/gateway/v1/diagnostics', {
        method: 'POST',
      });
      
      const data = await response.json();
      setDiagnosticsResult(JSON.stringify(data, null, 2));
    } catch (error) {
      console.error('Failed to run diagnostics:', error);
      setDiagnosticsResult(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setDiagnosing(false);
    }
  };

  return (
    <div className="settings-tab">
      {/* WebRTC Configuration */}
      <div className="settings-section">
        <h2>🌐 WebRTC Configuration</h2>
        <p className="description">
          Configure STUN/TURN servers for NAT traversal and WebRTC connectivity.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>STUN Server</h3>
            <p>Server for NAT discovery (format: stun:host:port)</p>
          </div>
          <div className="settings-control">
            <input
              type="text"
              className="settings-select"
              style={{ width: '300px' }}
              value={settings.stun_server || 'stun:stun.l.google.com:19302'}
              onChange={(e) => updateSetting('stun_server', e.target.value)}
              placeholder="stun:stun.l.google.com:19302"
              disabled={disabled}
            />
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>TURN Server</h3>
            <p>Relay server for restrictive NATs (format: turn:host:port)</p>
          </div>
          <div className="settings-control">
            <input
              type="text"
              className="settings-select"
              style={{ width: '300px' }}
              value={settings.turn_server || ''}
              onChange={(e) => updateSetting('turn_server', e.target.value)}
              placeholder="turn:turnserver.example.com:3478"
              disabled={disabled}
            />
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>TURN Username</h3>
            <p>Username for TURN server authentication</p>
          </div>
          <div className="settings-control">
            <input
              type="text"
              className="settings-select"
              style={{ width: '200px' }}
              value={settings.turn_username || ''}
              onChange={(e) => updateSetting('turn_username', e.target.value)}
              placeholder="username"
              disabled={disabled}
            />
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>TURN Password</h3>
            <p>Password for TURN server authentication</p>
          </div>
          <div className="settings-control">
            <input
              type="password"
              className="settings-select"
              style={{ width: '200px' }}
              value={settings.turn_password || ''}
              onChange={(e) => updateSetting('turn_password', e.target.value)}
              placeholder="password"
              disabled={disabled}
            />
          </div>
        </div>
      </div>

      {/* mDNS Configuration */}
      <div className="settings-section">
        <h2>📡 Service Discovery</h2>
        <p className="description">
          Configure mDNS/Bonjour for automatic network discovery.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Enable mDNS</h3>
            <p>Broadcast WomCast service on local network</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.mdns_enabled !== false}
                onChange={(e) => updateSetting('mdns_enabled', e.target.checked)}
                disabled={disabled}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* Network Diagnostics */}
      <div className="settings-section">
        <h2>🔧 Network Diagnostics</h2>
        <p className="description">
          Test network connectivity and diagnose connection issues.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Run Diagnostics</h3>
            <p>Check network configuration, ports, and connectivity</p>
          </div>
          <div className="settings-control">
            <button 
              className="settings-button"
              onClick={runDiagnostics}
              disabled={diagnosing || disabled}
            >
              {diagnosing ? 'Running...' : '🔍 Run Test'}
            </button>
          </div>
        </div>

        {diagnosticsResult && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            background: 'var(--card-bg, #1e1e2e)',
            borderRadius: '8px',
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            whiteSpace: 'pre-wrap',
            overflow: 'auto',
            maxHeight: '300px',
          }}>
            {diagnosticsResult}
          </div>
        )}
      </div>
    </div>
  );
};

export default NetworkTab;
