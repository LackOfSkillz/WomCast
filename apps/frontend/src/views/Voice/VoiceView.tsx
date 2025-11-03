import React, { useState } from 'react';
import { VoiceButton } from '../../components/VoiceButton';
import './VoiceView.css';

export interface VoiceViewProps {
  onSearch: (query: string) => void;
}

export const VoiceView: React.FC<VoiceViewProps> = ({ onSearch }) => {
  const [recentTranscripts, setRecentTranscripts] = useState<string[]>([]);

  const handleTranscript = (text: string) => {
    // Add to recent transcripts
    setRecentTranscripts(prev => [text, ...prev.slice(0, 4)]);

    // Route to search with the transcript
    if (text.trim()) {
      onSearch(text);
    }
  };

  const handleError = (error: string) => {
    console.error('Voice error:', error);
  };

  const handleRecentClick = (text: string) => {
    onSearch(text);
  };

  const clearRecents = () => {
    setRecentTranscripts([]);
  };

  return (
    <div className="voice-view">
      <div className="voice-header">
        <h1>Voice Search</h1>
        <p className="voice-subtitle">Press and hold the button to speak</p>
      </div>

      <div className="voice-content">
        <VoiceButton 
          onTranscript={handleTranscript}
          onError={handleError}
        />

        <div className="voice-tips">
          <h3>Voice Commands</h3>
          <ul>
            <li>Search for movies: "Show me action movies"</li>
            <li>Find TV shows: "Search for comedy series"</li>
            <li>Play music: "Play jazz music"</li>
            <li>Browse channels: "Show live TV channels"</li>
          </ul>
        </div>

        {recentTranscripts.length > 0 && (
          <div className="recent-transcripts">
            <div className="recent-header">
              <h3>Recent Searches</h3>
              <button className="clear-button" onClick={clearRecents}>
                Clear
              </button>
            </div>
            <div className="recent-list">
              {recentTranscripts.map((text, index) => (
                <button
                  key={index}
                  className="recent-item"
                  onClick={() => {
                    handleRecentClick(text);
                  }}
                >
                  <svg className="recent-icon" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                    <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                  </svg>
                  <span>{text}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
