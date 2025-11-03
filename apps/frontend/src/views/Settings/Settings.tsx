/**
 * Settings View - Tabbed settings interface with 5 sections
 * 
 * Tabs:
 * - Models: Whisper/Ollama model selection and download
 * - Privacy: Voice history, casting logs, data retention
 * - Pairing: QR pairing settings, PIN, paired devices
 * - CEC: HDMI-CEC enable/disable, device list, auto-switch
 * - Network: STUN/TURN servers, mDNS, network diagnostics
 */

import React, { useState, useEffect } from 'react';
import './Settings.css';
import ModelsTab from './tabs/ModelsTab';
import PrivacyTab from './tabs/PrivacyTab';
import PairingTab from './tabs/PairingTab';
import CECTab from './tabs/CECTab';
import NetworkTab from './tabs/NetworkTab';

export type Tab = 'models' | 'privacy' | 'pairing' | 'cec' | 'network';

export interface Settings {
  // Voice/AI models
  voice_model: string;
  llm_model: string | null;
  stt_enabled: boolean;
  tts_enabled: boolean;
  voice_language?: string;
  
  // Network shares
  auto_mount_shares: boolean;
  auto_index_shares: boolean;
  
  // Privacy flags
  analytics_enabled: boolean;
  crash_reporting: boolean;
  crash_reporting_enabled?: boolean;
  metadata_fetching_enabled: boolean;
  voice_history_days?: number;
  cast_history_days?: number;
  
  // Pairing
  pairing_enabled?: boolean;
  pairing_pin_length?: number;
  pairing_session_timeout?: number;
  
  // CEC
  cec_enabled?: boolean;
  cec_auto_switch?: boolean;
  
  // Network
  stun_server?: string;
  turn_server?: string;
  turn_username?: string;
  turn_password?: string;
  mdns_enabled?: boolean;
  network_diagnostics_enabled?: boolean;
  
  // UI preferences
  theme: 'dark' | 'light' | 'auto';
  language: string;
  grid_size: 'small' | 'medium' | 'large';
  autoplay_next: boolean;
  show_subtitles: boolean;
  
  // Playback settings
  default_volume: number;
  resume_threshold_seconds: number;
  skip_intro_seconds: number;
  
  // Performance
  cache_size_mb: number;
  thumbnail_quality: 'low' | 'medium' | 'high';
  
  // Notifications
  show_notifications: boolean;
  notification_duration_ms: number;
}

const SettingsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('models');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/settings/v1/settings');
      if (!response.ok) {
        throw new Error(`Failed to load settings: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const updateSetting = async (key: string, value: any) => {
    try {
      setSaving(true);
      
      const response = await fetch(`/api/settings/v1/settings/${key}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ key, value }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update setting: ${response.statusText}`);
      }
      
      // Update local state
      setSettings((prev) => prev ? { ...prev, [key]: value } : null);
    } catch (err) {
      console.error('Failed to update setting:', err);
      setError(err instanceof Error ? err.message : 'Failed to update setting');
    } finally {
      setSaving(false);
    }
  };

  const updateSettings = async (updates: Partial<Settings>) => {
    try {
      setSaving(true);
      
      const response = await fetch('/api/settings/v1/settings', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ settings: updates }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update settings: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSettings(data);
    } catch (err) {
      console.error('Failed to update settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  };

  const resetSettings = async () => {
    if (!window.confirm('Reset all settings to defaults? This cannot be undone.')) {
      return;
    }
    
    try {
      setSaving(true);
      
      const response = await fetch('/api/settings/v1/settings/reset', {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to reset settings: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSettings(data);
      setError(null);
    } catch (err) {
      console.error('Failed to reset settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to reset settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="settings-view">
        <div className="settings-loading">Loading settings...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="settings-view">
        <div className="settings-error">
          <h2>Error Loading Settings</h2>
          <p>{error}</p>
          <button onClick={loadSettings}>Retry</button>
        </div>
      </div>
    );
  }

  if (!settings) {
    return null;
  }

  return (
    <div className="settings-view">
      <header className="settings-header">
        <h1>Settings</h1>
        <div className="settings-actions">
          <button 
            className="btn-reset" 
            onClick={resetSettings}
            disabled={saving}
          >
            Reset to Defaults
          </button>
        </div>
      </header>

      <div className="settings-tabs">
        <button
          className={`tab ${activeTab === 'models' ? 'active' : ''}`}
          onClick={() => setActiveTab('models')}
        >
          🤖 Models
        </button>
        <button
          className={`tab ${activeTab === 'privacy' ? 'active' : ''}`}
          onClick={() => setActiveTab('privacy')}
        >
          🔒 Privacy
        </button>
        <button
          className={`tab ${activeTab === 'pairing' ? 'active' : ''}`}
          onClick={() => setActiveTab('pairing')}
        >
          📱 Pairing
        </button>
        <button
          className={`tab ${activeTab === 'cec' ? 'active' : ''}`}
          onClick={() => setActiveTab('cec')}
        >
          📺 CEC
        </button>
        <button
          className={`tab ${activeTab === 'network' ? 'active' : ''}`}
          onClick={() => setActiveTab('network')}
        >
          🌐 Network
        </button>
      </div>

      <div className="settings-content">
        {saving && <div className="settings-saving">Saving...</div>}
        
        {activeTab === 'models' && (
          <ModelsTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
          />
        )}
        
        {activeTab === 'privacy' && (
          <PrivacyTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
          />
        )}
        
        {activeTab === 'pairing' && (
          <PairingTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
          />
        )}
        
        {activeTab === 'cec' && (
          <CECTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
          />
        )}
        
        {activeTab === 'network' && (
          <NetworkTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
          />
        )}
      </div>
    </div>
  );
};

export default SettingsView;
