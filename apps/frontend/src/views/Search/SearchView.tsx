import React from 'react';
import { LibraryView, VoiceSearchCommand } from '../Library/LibraryView';

interface SearchViewProps {
  voiceQuery?: VoiceSearchCommand | null;
  onVoiceQueryHandled?: () => void;
}

export const SearchView: React.FC<SearchViewProps> = ({ voiceQuery, onVoiceQueryHandled }) => {
  return (
    <LibraryView
      voiceQuery={voiceQuery}
      onVoiceQueryHandled={onVoiceQueryHandled}
      title="Universal Search"
      subtitle="Blend lexical and semantic search across your entire WomCast library."
    />
  );
};
