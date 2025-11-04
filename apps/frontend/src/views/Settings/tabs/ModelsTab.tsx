import React from 'react';
import type { Settings } from '../../../types/settings';

interface ModelsTabProps {
  settings: Settings;
  updateSetting: (key: string, value: Settings[keyof Settings]) => Promise<void>;
  updateSettings: (updates: Partial<Settings>) => Promise<void>;
  disabled: boolean;
}

const ModelsTab: React.FC<ModelsTabProps> = ({ settings, updateSetting, disabled }) => {
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
              value={settings.voice_model || 'small'}
              onChange={(e) => updateSetting('voice_model', e.target.value)}
              disabled={disabled}
            >
              <option value="tiny">Tiny (fastest, 39M params)</option>
              <option value="base">Base (balanced, 74M params)</option>
              <option value="small">Small (better accuracy, 244M params)</option>
              <option value="medium">Medium (high accuracy, 769M params)</option>
              <option value="large">Large (best accuracy, 1550M params)</option>
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
              value={settings.llm_model || 'llama2'}
              onChange={(e) => updateSetting('llm_model', e.target.value)}
              disabled={disabled}
            >
              <option value="llama2">Llama 2 (7B)</option>
              <option value="llama2:13b">Llama 2 (13B)</option>
              <option value="mistral">Mistral (7B)</option>
              <option value="mixtral">Mixtral (8x7B)</option>
              <option value="codellama">Code Llama (7B)</option>
              <option value="phi">Phi-2 (2.7B)</option>
              <option value="gemma">Gemma (7B)</option>
            </select>
          </div>
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
