import React from 'react';
import './SettingsView.css';

interface SettingsSection {
  id: string;
  title: string;
  description: string;
  items: string[];
}

const settingsSections: SettingsSection[] = [
  {
    id: 'system',
    title: 'System',
    description: 'Device identity, HDMI-CEC, audio routing, and power behaviour.',
    items: [
      'Room name, language, and telemetry preferences',
      'HDMI-CEC device control and input sync',
      'Audio passthrough, loudness normalisation, and upmix profiles',
      'Automatic updates, nightly builds, and backup scheduling',
    ],
  },
  {
    id: 'extensions',
    title: 'Extensions & Apps',
    description: 'Enable optional connectors, emulators, and third-party experiences.',
    items: [
      'Install or remove partner connectors and add-on bundles',
      'Manage RetroArch cores, shaders, and playlist imports',
      'Toggle beta labs features like dashboards and kid mode',
      'Set default launcher for Steam Link, Moonlight, and Jellyfin',
    ],
  },
  {
    id: 'voice-ai',
    title: 'Voice & AI',
    description: 'Assistant intents, Whisper pipelines, and local model management.',
    items: [
      'Pair a microphone, set wake-word sensitivity, and PTT shortcuts',
      'Choose transcription backends (Whisper local vs. hosted)',
      'Configure AI responses, summarisation style, and fallback prompts',
      'Review privacy logs and delete cached transcripts',
    ],
  },
  {
    id: 'connectivity',
    title: 'Connectivity & Privacy',
    description: 'Networking, pairing, casting, and data controls.',
    items: [
      'Wi-Fi and Ethernet setup with captive portal support',
      'QR pairing, PIN reset, and mobile remote security',
      'Media share permissions and local network discovery',
      'Telemetry exports, privacy zones, and data retention policies',
    ],
  },
  {
    id: 'support',
    title: 'Support',
    description: 'Diagnostics, troubleshooting, and community resources.',
    items: [
      'Run health checks and view service uptime',
      'Download logs, screenshots, and system reports',
      'Contact support, join the Discord, or read docs',
      'Check warranty status and enrolled beta programs',
    ],
  },
];

export const SettingsView: React.FC = () => {
  return (
    <div className="settings-view">
      <header className="settings-view__header">
        <h1>Settings</h1>
        <p>Review and configure system services, extensions, and privacy controls.</p>
      </header>

      <div className="settings-view__grid">
        {settingsSections.map((section) => (
          <section key={section.id} className="settings-view__card">
            <h2>{section.title}</h2>
            <p className="settings-view__description">{section.description}</p>
            <ul>
              {section.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
};
