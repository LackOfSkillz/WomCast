import React, { useCallback, useEffect, useMemo, useState } from 'react';
import type { Settings } from '../../../types/settings';
import {
  cancelModelDownload,
  formatFileSize,
  getModelStatus,
  startModelDownload,
  type DownloadJobInfo,
  type ModelStatusResponse,
  type ModelVariant,
} from '../../../services/api';

interface ModelsTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
}

const ACTIVE_JOB_STATES: ReadonlySet<DownloadJobInfo['status']> = new Set(['pending', 'running']);

const ModelsTab: React.FC<ModelsTabProps> = ({ settings, updateSetting, disabled }) => {
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [statusError, setStatusError] = useState<string | null>(null);

  const loadModelStatus = useCallback(async () => {
    try {
      setStatusLoading(true);
      setStatusError(null);
      const response = await getModelStatus();
      setModelStatus(response);
    } catch (err) {
      setStatusError(err instanceof Error ? err.message : 'Failed to load model status');
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadModelStatus();
  }, [loadModelStatus]);

  useEffect(() => {
    if (!modelStatus?.active_job || !ACTIVE_JOB_STATES.has(modelStatus.active_job.status)) {
      return;
    }

    const timer = window.setInterval(() => {
      void loadModelStatus();
    }, 3000);

    return () => window.clearInterval(timer);
  }, [modelStatus?.active_job, loadModelStatus]);

  const voiceVariants = modelStatus?.voice.models ?? [];
  const llmVariants = modelStatus?.llm.models ?? [];

  const selectedVoiceModel = settings.voice_model || voiceVariants[0]?.name || '';
  const selectedLlmModel = settings.llm_model || llmVariants[0]?.name || '';

  const getJobById = useCallback(
    (jobId?: string | null): DownloadJobInfo | null => {
      if (!jobId || !modelStatus) {
        return null;
      }
      return modelStatus.jobs.find((job) => job.id === jobId) ?? null;
    },
    [modelStatus]
  );

  const handleDownload = useCallback(
    async (kind: 'voice' | 'llm', model: string) => {
      try {
        setStatusError(null);
        await startModelDownload(kind, model);
        await loadModelStatus();
      } catch (err) {
        setStatusError(err instanceof Error ? err.message : 'Failed to start download');
      }
    },
    [loadModelStatus]
  );

  const handleCancel = useCallback(
    async (jobId: string) => {
      try {
        setStatusError(null);
        await cancelModelDownload(jobId);
        await loadModelStatus();
      } catch (err) {
        setStatusError(err instanceof Error ? err.message : 'Failed to cancel download');
      }
    },
    [loadModelStatus]
  );

  const renderStatus = useCallback(
    (variant: ModelVariant): string => {
      const job = getJobById(variant.download_job_id);

      switch (variant.status) {
        case 'ready':
          return 'Installed';
        case 'missing':
          return 'Not installed';
        case 'downloading': {
          if (job?.progress != null) {
            return `Downloading ${Math.round(job.progress * 100)}%`;
          }
          if (job?.downloaded_bytes != null && job?.total_bytes != null && job.total_bytes > 0) {
            return `Downloading ${formatFileSize(job.downloaded_bytes)} / ${formatFileSize(job.total_bytes)}`;
          }
          return 'Downloading…';
        }
        case 'failed':
          return variant.error ? `Failed: ${variant.error}` : 'Failed';
        case 'cancelled':
          return 'Cancelled';
        default:
          return 'Unknown';
      }
    },
    [getJobById]
  );

  const whisperStorageText = useMemo(() => {
    if (!modelStatus) {
      return null;
    }
    const { disk } = modelStatus.voice;
    return `Stored at ${disk.path} • Free ${formatFileSize(disk.free_bytes)} of ${formatFileSize(disk.total_bytes)}`;
  }, [modelStatus]);

  const llmStorageText = useMemo(() => {
    if (!modelStatus) {
      return null;
    }
    const { disk } = modelStatus.llm;
    return `Stored at ${disk.path} • Free ${formatFileSize(disk.free_bytes)} of ${formatFileSize(disk.total_bytes)}`;
  }, [modelStatus]);

  return (
    <div className="settings-tab">
      {/* Whisper Model */}
      <div className="settings-section">
        <h2>🎤 Voice Recognition (Whisper)</h2>
        <p className="description">
          Configure speech-to-text using OpenAI's Whisper model. Larger models provide better accuracy but require more resources.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Whisper Model</h3>
            <p>Choose the model size for voice transcription</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={selectedVoiceModel}
              onChange={(e) => updateSetting('voice_model', e.target.value)}
              disabled={disabled || statusLoading}
            >
              {voiceVariants.map((variant) => (
                <option
                  key={variant.name}
                  value={variant.name}
                  disabled={!variant.installed && variant.name !== selectedVoiceModel}
                >
                  {variant.display_name}
                  {variant.estimated_size_bytes ? ` (${formatFileSize(variant.estimated_size_bytes)})` : ''}
                  {!variant.installed ? ' • install required' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Speech-to-Text</h3>
            <p>Enable voice recognition for commands</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.stt_enabled !== false}
                onChange={(e) => updateSetting('stt_enabled', e.target.checked)}
                disabled={disabled}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-label">
            <h3>Voice Language</h3>
            <p>Primary language for voice recognition</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={settings.voice_language || 'en'}
              onChange={(e) => updateSetting('voice_language', e.target.value)}
              disabled={disabled}
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
            </select>
          </div>
        </div>

        <div className="model-subsection">
          <h3>Available Whisper Models</h3>
          {statusError && (
            <div className="model-status-error" role="alert">
              {statusError}
            </div>
          )}
          {statusLoading && <div className="model-status-loading">Refreshing model status…</div>}
          <ul className="settings-list">
            {voiceVariants.map((variant) => {
              const job = getJobById(variant.download_job_id);
              const showDownload = ['missing', 'failed', 'cancelled'].includes(variant.status);
              const showCancel = variant.status === 'downloading' && job?.id;

              return (
                <li key={variant.name} className="settings-list-item">
                  <div className="settings-list-item-info">
                    <h4>{variant.display_name}</h4>
                    <p>
                      {renderStatus(variant)}
                      {variant.estimated_size_bytes ? ` • ${formatFileSize(variant.estimated_size_bytes)}` : ''}
                      {variant.installed_size_bytes && variant.installed_size_bytes !== variant.estimated_size_bytes
                        ? ` • on disk ${formatFileSize(variant.installed_size_bytes)}`
                        : ''}
                    </p>
                  </div>
                  <div className="settings-list-item-actions">
                    {showDownload && (
                      <button
                        className="settings-button"
                        onClick={() => handleDownload('voice', variant.name)}
                        disabled={disabled || statusLoading}
                      >
                        Download
                      </button>
                    )}
                    {showCancel && job && (
                      <button
                        className="settings-button secondary"
                        onClick={() => handleCancel(job.id)}
                        disabled={disabled || statusLoading}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {whisperStorageText && <p className="model-storage-note">{whisperStorageText}</p>}
        </div>
      </div>

      {/* Ollama LLM */}
      <div className="settings-section">
        <h2>🧠 Language Model (Ollama)</h2>
        <p className="description">
          Configure the AI language model for voice interactions and metadata enrichment.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Ollama Model</h3>
            <p>Select which model to use for AI responses</p>
          </div>
          <div className="settings-control">
            <select
              className="settings-select"
              value={selectedLlmModel}
              onChange={(e) => updateSetting('llm_model', e.target.value)}
              disabled={disabled || statusLoading}
            >
              {llmVariants.map((variant) => (
                <option
                  key={variant.name}
                  value={variant.name}
                  disabled={!variant.installed && variant.name !== selectedLlmModel}
                >
                  {variant.display_name}
                  {variant.estimated_size_bytes ? ` (${formatFileSize(variant.estimated_size_bytes)})` : ''}
                  {!variant.installed ? ' • install required' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="model-subsection">
          <h3>Available Ollama Models</h3>
          <ul className="settings-list">
            {llmVariants.map((variant) => {
              const job = getJobById(variant.download_job_id);
              const showDownload = ['missing', 'failed', 'cancelled'].includes(variant.status);
              const showCancel = variant.status === 'downloading' && job?.id;

              return (
                <li key={variant.name} className="settings-list-item">
                  <div className="settings-list-item-info">
                    <h4>{variant.display_name}</h4>
                    <p>
                      {renderStatus(variant)}
                      {variant.estimated_size_bytes ? ` • ${formatFileSize(variant.estimated_size_bytes)}` : ''}
                      {variant.installed_size_bytes && variant.installed_size_bytes !== variant.estimated_size_bytes
                        ? ` • on disk ${formatFileSize(variant.installed_size_bytes)}`
                        : ''}
                    </p>
                  </div>
                  <div className="settings-list-item-actions">
                    {showDownload && (
                      <button
                        className="settings-button"
                        onClick={() => handleDownload('llm', variant.name)}
                        disabled={disabled || statusLoading}
                      >
                        Download
                      </button>
                    )}
                    {showCancel && job && (
                      <button
                        className="settings-button secondary"
                        onClick={() => handleCancel(job.id)}
                        disabled={disabled || statusLoading}
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
          {llmStorageText && <p className="model-storage-note">{llmStorageText}</p>}
        </div>
      </div>

      {/* Text-to-Speech */}
      <div className="settings-section">
        <h2>🔊 Text-to-Speech</h2>
        <p className="description">
          Enable voice responses for AI interactions.
        </p>
        
        <div className="settings-row">
          <div className="settings-label">
            <h3>Enable TTS</h3>
            <p>Have the AI speak responses aloud</p>
          </div>
          <div className="settings-control">
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={settings.tts_enabled === true}
                onChange={(e) => updateSetting('tts_enabled', e.target.checked)}
                disabled={disabled}
              />
              <span className="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelsTab;
