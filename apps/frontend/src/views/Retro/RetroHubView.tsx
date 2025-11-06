import React from 'react';
import './RetroHubView.css';

interface RetroCollection {
  id: string;
  title: string;
  description: string;
  systems: string[];
}

interface RetroAction {
  id: string;
  title: string;
  detail: string;
  icon: string;
}

const collections: RetroCollection[] = [
  {
    id: 'recent',
    title: 'Recently Played',
    description: 'Continue where you left off with quick resume save states.',
    systems: ['SNES', 'Genesis', 'PSX'],
  },
  {
    id: 'playlists',
    title: 'Curated Playlists',
    description: 'Community favourites and seasonal spotlights.',
    systems: ['NES', 'Arcade', 'Game Boy'],
  },
  {
    id: 'arcade-night',
    title: 'Arcade Night',
    description: 'Synchronized cabinets and party-ready high score chasing.',
    systems: ['MAME', 'Neo Geo', 'CPS2'],
  },
];

const retroActions: RetroAction[] = [
  {
    id: 'launch-retroarch',
    title: 'Launch RetroArch',
    detail: 'Full emulator front-end with per-core settings and overlays.',
    icon: '🚀',
  },
  {
    id: 'configure-controllers',
    title: 'Controller Lab',
    detail: 'Map gamepads, set deadzones, and apply per-system profiles.',
    icon: '🎮',
  },
  {
    id: 'netplay',
    title: 'Netplay Lobby',
    detail: 'Host or join rollback-ready cooperative sessions.',
    icon: '🌐',
  },
  {
    id: 'achievements',
    title: 'Retro Achievements',
    detail: 'Connect to retroachievements.org and sync progress.',
    icon: '🏆',
  },
];

export const RetroHubView: React.FC = () => {
  return (
    <div className="retro-view">
      <header className="retro-view__header">
        <h1>Retro Hub</h1>
        <p>
          Manage emulators, controller profiles, playlists, and cloud-sync save states for your
          retro library.
        </p>
      </header>

      <section className="retro-view__collections">
        <h2>Collections</h2>
        <div className="retro-view__collection-grid">
          {collections.map((collection) => (
            <article key={collection.id} className="retro-view__collection-card">
              <h3>{collection.title}</h3>
              <p>{collection.description}</p>
              <div className="retro-view__systems" aria-label="Supported systems">
                {collection.systems.map((system) => (
                  <span key={system}>{system}</span>
                ))}
              </div>
              <button type="button">Open</button>
            </article>
          ))}
        </div>
      </section>

      <section className="retro-view__actions">
        <h2>Actions</h2>
        <div className="retro-view__action-grid">
          {retroActions.map((action) => (
            <button key={action.id} type="button" className="retro-view__action-card">
              <span className="retro-view__action-icon" aria-hidden="true">
                {action.icon}
              </span>
              <div className="retro-view__action-copy">
                <h3>{action.title}</h3>
                <p>{action.detail}</p>
              </div>
            </button>
          ))}
        </div>
      </section>

      <section className="retro-view__status">
        <h2>Sync Status</h2>
        <div className="retro-view__status-card">
          <div>
            <h3>Profiles & Saves</h3>
            <p>Cloud sync active. Last upload completed 12 minutes ago.</p>
          </div>
          <button type="button">Manage Sync</button>
        </div>
      </section>
    </div>
  );
};
