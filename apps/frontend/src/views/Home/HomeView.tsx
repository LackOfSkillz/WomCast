import React from 'react';
import './HomeView.css';

export type HomeNavTarget =
  | 'library'
  | 'search'
  | 'connectors'
  | 'livetv'
  | 'retro'
  | 'voice'
  | 'settings'
  | 'cast';

interface HomeViewProps {
  onNavigate: (target: HomeNavTarget) => void;
  online: boolean;
}

const quickLinks: Array<{
  target: HomeNavTarget;
  icon: string;
  title: string;
  description: string;
}> = [
  {
    target: 'library',
    icon: '📚',
    title: 'Library',
    description: 'Browse local media with artwork, subtitles, and resume points.',
  },
  {
    target: 'search',
    icon: '🔍',
    title: 'Universal Search',
    description: 'Blend text and semantic results across your entire catalog.',
  },
  {
    target: 'connectors',
    icon: '🌐',
    title: 'Connectors',
    description: 'Jump into free content from PBS, NASA, Jamendo, and more.',
  },
  {
    target: 'livetv',
    icon: '📺',
    title: 'Live TV',
    description: 'Switch to IPTV playlists and OTA streams with guide metadata.',
  },
  {
    target: 'retro',
    icon: '🕹️',
    title: 'Retro Hub',
    description: 'Launch RetroArch profiles, controller maps, and save states.',
  },
  {
    target: 'voice',
    icon: '🎤',
    title: 'Voice & AI',
    description: 'Transcribe with Whisper, ask natural questions, and run intents.',
  },
  {
    target: 'settings',
    icon: '⚙️',
    title: 'Settings',
    description: 'Configure models, privacy, pairing, HDMI-CEC, and networking.',
  },
  {
    target: 'cast',
    icon: '📱',
    title: 'Casting',
    description: 'Pair phones via QR, manage PIN sessions, and open the LAN remote.',
  },
];

export const HomeView: React.FC<HomeViewProps> = ({ onNavigate, online }) => {
  return (
    <div className="home-view">
      <section className="home-view__hero">
        <div className="home-view__hero-content">
          <h1>Welcome to WomCast</h1>
          <p>
            Your media, streaming connectors, and voice AI all live here. Choose a section below
            to get started or pick up where you left off.
          </p>
          <div className="home-view__hero-actions">
            <button
              className="home-view__primary-btn"
              type="button"
              onClick={() => onNavigate('library')}
            >
              Explore Library
            </button>
            <button
              className="home-view__secondary-btn"
              type="button"
              onClick={() => onNavigate('search')}
            >
              Run a Search
            </button>
          </div>
        </div>
        <div className="home-view__hero-bubble" aria-hidden="true" />
      </section>

      {!online && (
        <section className="home-view__status" role="status" aria-live="polite">
          <span>⚠️ Offline mode:</span> Some cloud connectors and pairing features may be limited
          until you reconnect.
        </section>
      )}

      <section className="home-view__quick-links">
        <h2>Quick Access</h2>
        <div className="home-view__grid">
          {quickLinks.map((link) => (
            <button
              key={link.target}
              type="button"
              className="home-view__card"
              onClick={() => onNavigate(link.target)}
            >
              <span className="home-view__card-icon" aria-hidden="true">
                {link.icon}
              </span>
              <div className="home-view__card-body">
                <h3>{link.title}</h3>
                <p>{link.description}</p>
              </div>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
};
