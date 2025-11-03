import React from 'react';

interface NetworkTabProps {
  settings: {
    stun_server?: string;
    turn_server?: string;
    turn_username?: string;
    turn_password?: string;
    mdns_enabled?: boolean;
    network_diagnostics_enabled?: boolean;
  };
  updateSetting: (key: string, value: any) => Promise<void>;
  updateSettings: (updates: any) => Promise<void>;
}

const NetworkTab: React.FC<NetworkTabProps> = ({ settings, updateSetting }) => {
  const [diagnosing, setDiagnosing] = React.useState(false);
  const [diagnosticsResult, setDiagnosticsResult] = React.useState<string | null>(null);

  const runDiagnostics = async () => {
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
              disabled={diagnosing}
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
