import React from 'react';

interface PrivacyTabProps {
  settings: {
    analytics_enabled?: boolean;
    crash_reporting_enabled?: boolean;
    metadata_fetching_enabled?: boolean;
    voice_history_days?: number;
    cast_history_days?: number;
  };
  updateSetting: (key: string, value: any) => Promise<void>;
  updateSettings: (updates: any) => Promise<void>;
}

const PrivacyTab: React.FC<PrivacyTabProps> = ({ settings, updateSetting }) => {
  return (
    <div className="settings-tab">
      {/* Data Collection */}
      <div className="settings-section">
        <h2>📊 Data Collection</h2>
        <p className="description">
          Control what data WomCast collects to improve your experience.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Analytics</h3>
            <p>Send anonymous usage statistics to improve WomCast</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.analytics_enabled === true}
                onChange={(e) => updateSetting('analytics_enabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Crash Reporting</h3>
            <p>Automatically send crash reports to help fix bugs</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.crash_reporting_enabled === true}
                onChange={(e) => updateSetting('crash_reporting_enabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* Metadata & Enrichment */}
      <div className="settings-section">
        <h2>🎬 Metadata & Enrichment</h2>
        <p className="description">
          Control fetching of movie/TV show metadata from external sources.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Metadata Fetching</h3>
            <p>Fetch posters, descriptions, and ratings from TMDB/TVDB</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.metadata_fetching_enabled !== false}
                onChange={(e) => updateSetting('metadata_fetching_enabled', e.target.checked)}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>

      {/* History & Retention */}
      <div className="settings-section">
        <h2>🗂️ History & Retention</h2>
        <p className="description">
          Manage how long WomCast keeps your activity history.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Voice History</h3>
            <p>Automatically delete voice recordings after this many days</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={settings.voice_history_days || 30}
              onChange={(e) => updateSetting('voice_history_days', parseInt(e.target.value))}
            >
              <option value="0">Never delete</option>
              <option value="1">1 day</option>
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
              <option value="365">1 year</option>
            </select>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Cast History</h3>
            <p>Automatically delete casting logs after this many days</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={settings.cast_history_days || 90}
              onChange={(e) => updateSetting('cast_history_days', parseInt(e.target.value))}
            >
              <option value="0">Never delete</option>
              <option value="1">1 day</option>
              <option value="7">7 days</option>
              <option value="30">30 days</option>
              <option value="90">90 days</option>
              <option value="365">1 year</option>
            </select>
          </div>
        </div>
      </div>

      {/* Data Export & Deletion */}
      <div className="settings-section">
        <h2>💾 Data Export & Deletion</h2>
        <p className="description">
          Export or permanently delete all your data.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Export Data</h3>
            <p>Download a copy of all your settings, history, and activity</p>
          </div>
          <div className="settings-control">
            <button 
              className="settings-button secondary"
              onClick={() => {/* TODO: implement data export */}}
            >
              Export
            </button>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Delete All Data</h3>
            <p>Permanently delete all voice recordings, cast history, and settings</p>
          </div>
          <div className="settings-control">
            <button 
              className="settings-button secondary"
              onClick={() => {
                if (confirm('Are you sure you want to delete all your data? This cannot be undone.')) {
                  /* TODO: implement data deletion */
                }
              }}
            >
              Delete All
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrivacyTab;
