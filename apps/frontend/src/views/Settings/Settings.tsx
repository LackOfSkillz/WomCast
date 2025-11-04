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

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';
import {
  getSettings,
  resetAllSettings,
  updateMultipleSettings,
  updateSingleSetting,
  type SettingsResponse,
} from '../../services/api';
import type { Settings } from '../../types/settings';
import './Settings.css';
import ModelsTab from './tabs/ModelsTab';
import PrivacyTab from './tabs/PrivacyTab';
import PairingTab from './tabs/PairingTab';
import CECTab from './tabs/CECTab';
import NetworkTab from './tabs/NetworkTab';

export type Tab = 'models' | 'privacy' | 'pairing' | 'cec' | 'network';

const OFFLINE_STATUS = 'Offline mode: settings are read-only until you reconnect.';

const normalizeSettings = (raw: SettingsResponse): Settings => {
  const normalized: SettingsResponse & { crash_reporting?: boolean } = { ...raw };

  if (
    normalized.crash_reporting_enabled === undefined &&
    normalized.crash_reporting !== undefined
  ) {
    normalized.crash_reporting_enabled = normalized.crash_reporting ?? false;
  }

  normalized.voice_model = normalized.voice_model ?? 'small';
  normalized.llm_model = normalized.llm_model ?? 'llama2';
  normalized.stt_enabled = normalized.stt_enabled ?? true;
  normalized.tts_enabled = normalized.tts_enabled ?? false;
  normalized.voice_language = normalized.voice_language ?? 'en';

  normalized.auto_mount_shares = normalized.auto_mount_shares ?? false;
  normalized.auto_index_shares = normalized.auto_index_shares ?? false;

  normalized.analytics_enabled = normalized.analytics_enabled ?? false;
  normalized.crash_reporting_enabled = normalized.crash_reporting_enabled ?? false;
  normalized.metadata_fetching_enabled = normalized.metadata_fetching_enabled ?? true;
  normalized.voice_history_days = normalized.voice_history_days ?? 30;
  normalized.cast_history_days = normalized.cast_history_days ?? 90;

  normalized.pairing_enabled = normalized.pairing_enabled ?? true;
  normalized.pairing_pin_length = normalized.pairing_pin_length ?? 6;
  normalized.pairing_session_timeout = normalized.pairing_session_timeout ?? 300;

  normalized.cec_enabled = normalized.cec_enabled ?? true;
  normalized.cec_auto_switch = normalized.cec_auto_switch ?? true;

  normalized.stun_server = normalized.stun_server ?? 'stun:stun.l.google.com:19302';
  normalized.turn_server = normalized.turn_server ?? '';
  normalized.turn_username = normalized.turn_username ?? '';
  normalized.turn_password = normalized.turn_password ?? '';
  normalized.mdns_enabled = normalized.mdns_enabled ?? true;
  normalized.network_diagnostics_enabled = normalized.network_diagnostics_enabled ?? false;

  normalized.theme = normalized.theme ?? 'dark';
  normalized.language = normalized.language ?? 'en';
  normalized.grid_size = normalized.grid_size ?? 'medium';
  normalized.autoplay_next = normalized.autoplay_next ?? true;
  normalized.show_subtitles = normalized.show_subtitles ?? true;

  normalized.default_volume = normalized.default_volume ?? 80;
  normalized.resume_threshold_seconds = normalized.resume_threshold_seconds ?? 60;
  normalized.skip_intro_seconds = normalized.skip_intro_seconds ?? 0;

  normalized.cache_size_mb = normalized.cache_size_mb ?? 500;
  normalized.thumbnail_quality = normalized.thumbnail_quality ?? 'medium';

  normalized.show_notifications = normalized.show_notifications ?? true;
  normalized.notification_duration_ms = normalized.notification_duration_ms ?? 3000;

  delete (normalized as Record<string, unknown>).crash_reporting;

  return normalized as Settings;
};

const SettingsView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('models');
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const hasLoadedOnce = useRef(false);
  const { online } = useNetworkStatus();

  // Load settings on mount
  const loadSettings = useCallback(async () => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
      setLoading(false);
      if (!hasLoadedOnce.current) {
        setError('Connect to the network to load settings.');
      }
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setStatusMessage(null);

  const data = await getSettings();
  setSettings(normalizeSettings(data));
      hasLoadedOnce.current = true;
    } catch (err) {
      console.error('Failed to load settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [online]);

  useEffect(() => {
    void loadSettings();
  }, [loadSettings]);

  useEffect(() => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
    } else if (statusMessage === OFFLINE_STATUS) {
      setStatusMessage(null);
    }
  }, [online, statusMessage]);

  const updateSetting = useCallback(async (key: string, value: unknown) => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
      return;
    }

    try {
      setSaving(true);
      await updateSingleSetting(key, value);

      setSettings((prev) => {
        if (!prev) {
          return prev;
        }

        const updated = { ...prev, [key]: value } as SettingsResponse;
        return normalizeSettings(updated);
      });
      setError(null);
    } catch (err) {
      console.error('Failed to update setting:', err);
      setError(err instanceof Error ? err.message : 'Failed to update setting');
    } finally {
      setSaving(false);
    }
  }, [online]);

  const updateSettings = useCallback(async (updates: Partial<Settings>) => {
    if (!online) {
      setStatusMessage(OFFLINE_STATUS);
      return;
    }

    try {
      setSaving(true);
  const data = await updateMultipleSettings(updates);
  setSettings(normalizeSettings(data));
      setError(null);
      hasLoadedOnce.current = true;
    } catch (err) {
      console.error('Failed to update settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to update settings');
    } finally {
      setSaving(false);
    }
  }, [online]);

  const resetSettings = useCallback(async () => {
    if (!window.confirm('Reset all settings to defaults? This cannot be undone.')) {
      return;
    }
    
    try {
      setSaving(true);
  const data = await resetAllSettings();
  setSettings(normalizeSettings(data));
      setError(null);
      setStatusMessage('Settings restored to defaults.');
    } catch (err) {
      console.error('Failed to reset settings:', err);
      setError(err instanceof Error ? err.message : 'Failed to reset settings');
    } finally {
      setSaving(false);
    }
  }, []);

  const controlsDisabled = saving || !online;

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
          <button
            onClick={() => {
              void loadSettings();
            }}
          >
            Retry
          </button>
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
            disabled={controlsDisabled}
          >
            Reset to Defaults
          </button>
        </div>
      </header>

      {statusMessage && (
        <div className="settings-status" role="status" aria-live="polite">
          {statusMessage}
        </div>
      )}

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
            disabled={controlsDisabled}
          />
        )}
        
        {activeTab === 'privacy' && (
          <PrivacyTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
            disabled={controlsDisabled}
            reloadSettings={loadSettings}
          />
        )}
        
        {activeTab === 'pairing' && (
          <PairingTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
            disabled={controlsDisabled}
          />
        )}
        
        {activeTab === 'cec' && (
          <CECTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
            disabled={controlsDisabled}
          />
        )}
        
        {activeTab === 'network' && (
          <NetworkTab
            settings={settings}
            updateSetting={updateSetting}
            updateSettings={updateSettings}
            disabled={controlsDisabled}
          />
        )}
      </div>
    </div>
  );
};

export default SettingsView;
