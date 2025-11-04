import React from 'react';
import type { Settings } from '../../../types/settings';
import {
  deletePrivacyData,
  deleteVoiceHistory,
  exportPrivacyData,
} from '../../../services/api';

interface PrivacyTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
  reloadSettings: () => Promise<void>;
}

const PrivacyTab: React.FC<PrivacyTabProps> = ({
  settings,
  updateSetting,
  disabled,
  reloadSettings,
}) => {
  const [deletingVoiceHistory, setDeletingVoiceHistory] = React.useState(false);
  const [exportingData, setExportingData] = React.useState(false);
  const [deletingAllData, setDeletingAllData] = React.useState(false);
  const abortController = React.useRef<AbortController | null>(null);

  React.useEffect(
    () => () => {
      abortController.current?.abort();
    },
    [],
  );

  const handleDeleteVoiceHistory = async () => {
    if (disabled) {
      return;
    }

    if (!confirm('Delete all saved voice transcriptions? This cannot be undone.')) {
      return;
    }

    try {
      setDeletingVoiceHistory(true);
      const data = await deleteVoiceHistory();
      alert(data.message || 'Voice history deleted.');
    } catch (error) {
      console.error('Failed to delete voice history:', error);
      alert('Failed to delete voice history. Please try again.');
    } finally {
      setDeletingVoiceHistory(false);
    }
  };

  const handleExportData = async () => {
    if (disabled) {
      return;
    }

    try {
      setExportingData(true);
      if (abortController.current) {
        abortController.current.abort();
      }

      abortController.current = new AbortController();
      const response = await exportPrivacyData(abortController.current.signal);
      const blob = await response.blob();
      let filename = `womcast-privacy-export-${new Date().toISOString()}.json`;
      const disposition = response.headers.get('Content-Disposition');
      if (disposition) {
        const match = disposition.match(/filename="?([^";]+)"?/i);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        console.info('Privacy export aborted');
        return;
      }
      console.error('Failed to export data:', error);
      alert('Failed to export data. Please try again.');
    } finally {
      setExportingData(false);
      abortController.current = null;
    }
  };

  const handleDeleteAllData = async () => {
    if (disabled) {
      return;
    }

    if (!confirm('Are you sure you want to delete all your data? This cannot be undone.')) {
      return;
    }

    try {
      setDeletingAllData(true);
      const data = await deletePrivacyData();
      await reloadSettings();
      alert(data.message || 'All data has been deleted.');
    } catch (error) {
      console.error('Failed to delete data:', error);
      alert('Failed to delete data. Please try again.');
    } finally {
      setDeletingAllData(false);
    }
  };

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
                disabled={disabled}
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
                disabled={disabled}
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
                disabled={disabled}
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
              onChange={(e) => updateSetting('voice_history_days', parseInt(e.target.value, 10))}
              disabled={disabled}
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
            <h3>Delete Voice History</h3>
            <p>Permanently delete all saved voice transcriptions</p>
          </div>
          <div className="settings-control">
            <button
              className="settings-button secondary"
              onClick={handleDeleteVoiceHistory}
              disabled={deletingVoiceHistory || disabled}
            >
              {deletingVoiceHistory ? 'Deleting...' : 'Delete Voice History'}
            </button>
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
              onChange={(e) => updateSetting('cast_history_days', parseInt(e.target.value, 10))}
              disabled={disabled}
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
              onClick={handleExportData}
              disabled={exportingData || disabled}
            >
              {exportingData ? 'Preparing...' : 'Export'}
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
              onClick={handleDeleteAllData}
              disabled={deletingAllData || disabled}
            >
              {deletingAllData ? 'Deleting...' : 'Delete All'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PrivacyTab;
