import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VoiceView } from './VoiceView';

const mockVoiceButton = vi.fn(
  ({ onTranscript }: { onTranscript: (text: string) => void }) => (
    <button onClick={() => onTranscript('test search query')}>Mock Voice Button</button>
  )
);

vi.mock('../../components/VoiceButton', () => ({
  VoiceButton: (props: { onTranscript: (text: string) => void }) => mockVoiceButton(props),
}));

describe('VoiceView', () => {
  beforeEach(() => {
    mockVoiceButton.mockClear();
    mockVoiceButton.mockImplementation(({ onTranscript }: { onTranscript: (text: string) => void }) => (
      <button onClick={() => onTranscript('test search query')}>Mock Voice Button</button>
    ));
  });

  it('renders the voice search view', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    expect(screen.getByText('Voice Search')).toBeDefined();
    expect(screen.getByText('Press and hold the button to speak')).toBeDefined();
  });

  it('displays voice command tips', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    expect(screen.getByText('Voice Commands')).toBeDefined();
    expect(screen.getByText(/Show me action movies/)).toBeDefined();
    expect(screen.getByText(/Search for comedy series/)).toBeDefined();
    expect(screen.getByText(/Play jazz music/)).toBeDefined();
    expect(screen.getByText(/Show live TV channels/)).toBeDefined();
  });

  it('calls onSearch when transcript is received', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    const voiceButton = screen.getByText('Mock Voice Button');
    fireEvent.click(voiceButton);

    expect(mockOnSearch).toHaveBeenCalledWith('test search query');
  });

  it('displays recent transcripts', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    const voiceButton = screen.getByText('Mock Voice Button');
    fireEvent.click(voiceButton);

    expect(screen.getByText('Recent Searches')).toBeDefined();
    expect(screen.getByText('test search query')).toBeDefined();
  });

  it('allows clicking recent transcripts to search again', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    // First search
    const voiceButton = screen.getByText('Mock Voice Button');
    fireEvent.click(voiceButton);

    expect(mockOnSearch).toHaveBeenCalledWith('test search query');

    // Click the recent item
    const recentItem = screen.getByText('test search query');
    fireEvent.click(recentItem);

    expect(mockOnSearch).toHaveBeenCalledTimes(2);
    expect(mockOnSearch).toHaveBeenLastCalledWith('test search query');
  });

  it('clears recent transcripts when clear button is clicked', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    // Add a transcript
    const voiceButton = screen.getByText('Mock Voice Button');
    fireEvent.click(voiceButton);

    expect(screen.getByText('test search query')).toBeDefined();

    // Clear recents
    const clearButton = screen.getByText('Clear');
    fireEvent.click(clearButton);

    // Recent searches section should not be visible
    expect(screen.queryByText('Recent Searches')).toBeNull();
  });

  it('limits recent transcripts to 5 items', () => {
    const mockOnSearch = vi.fn();
    render(<VoiceView onSearch={mockOnSearch} />);

    const voiceButton = screen.getByText('Mock Voice Button');

    // Add 6 transcripts
    for (let i = 0; i < 6; i++) {
      fireEvent.click(voiceButton);
    }

    // Should only show 5 items (all with same text in this mock)
    const recentItems = screen.getAllByText('test search query');
    expect(recentItems.length).toBe(5);
  });

  it('ignores empty transcripts', () => {
    const mockOnSearch = vi.fn();
    mockVoiceButton.mockImplementationOnce(({ onTranscript }: { onTranscript: (text: string) => void }) => (
      <button onClick={() => onTranscript('  ')}>Mock Voice Button</button>
    ));

    render(<VoiceView onSearch={mockOnSearch} />);

    const voiceButton = screen.getByText('Mock Voice Button');
    fireEvent.click(voiceButton);

    expect(mockOnSearch).not.toHaveBeenCalled();
    expect(screen.queryByText('Recent Searches')).toBeNull();
  });
});
