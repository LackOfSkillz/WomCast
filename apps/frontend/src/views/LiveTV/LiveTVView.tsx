import { useState, useEffect } from 'react';
import { getLiveTVChannels, playLiveTVChannel, type LiveTVChannel } from '../../services/api';
import './LiveTVView.css';

export function LiveTVView() {
  const [channels, setChannels] = useState<LiveTVChannel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
  const [groups, setGroups] = useState<string[]>([]);

  const loadChannels = async () => {
    setLoading(true);
    setError(null);
    try {
      const channelList = await getLiveTVChannels(selectedGroup ?? undefined, 100);
      setChannels(channelList);

      // Extract unique groups
      const uniqueGroups = Array.from(
        new Set(channelList.map((ch) => ch.group_title).filter((g): g is string => g !== null))
      );
      setGroups(uniqueGroups.sort());
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load channels';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadChannels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedGroup]);

  const handlePlay = async (channel: LiveTVChannel) => {
    try {
      await playLiveTVChannel(channel.stream_url, channel.name);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to play channel';
      setError(message);
    }
  };

  const handleGroupFilter = (group: string | null) => {
    setSelectedGroup(group);
  };

  if (loading) {
    return (
      <div className="livetv-view">
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading channels...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="livetv-view">
        <div className="error">
          <p>❌ {error}</p>
          <button onClick={() => { void loadChannels(); }}>Retry</button>
        </div>
      </div>
    );
  }

  if (channels.length === 0) {
    return (
      <div className="livetv-view">
        <div className="empty">
          <p>📺 No live TV channels found</p>
          <p className="hint">Upload an M3U playlist to get started</p>
        </div>
      </div>
    );
  }

  return (
    <div className="livetv-view">
      <div className="livetv-header">
        <h1>📺 Live TV</h1>
        <div className="group-filter">
          <button
            className={selectedGroup === null ? 'active' : ''}
            onClick={() => { handleGroupFilter(null); }}
          >
            All Channels ({channels.length})
          </button>
          {groups.map((group) => {
            const count = channels.filter((ch) => ch.group_title === group).length;
            return (
              <button
                key={group}
                className={selectedGroup === group ? 'active' : ''}
                onClick={() => { handleGroupFilter(group); }}
              >
                {group} ({count})
              </button>
            );
          })}
        </div>
      </div>

      <div className="channel-grid">
        {channels.map((channel) => (
          <div key={channel.id} className="channel-card">
            <div className="channel-logo">
              {channel.logo_url ? (
                <img src={channel.logo_url} alt={channel.name} />
              ) : (
                <div className="logo-placeholder">📺</div>
              )}
            </div>
            <div className="channel-info">
              <h3 className="channel-name">{channel.name}</h3>
              {channel.group_title && (
                <p className="channel-group">{channel.group_title}</p>
              )}
              {channel.language && (
                <p className="channel-language">🌐 {channel.language}</p>
              )}
            </div>
            <button
              className="play-button"
              onClick={() => { void handlePlay(channel); }}
              aria-label={`Play ${channel.name}`}
            >
              ▶ Play
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
