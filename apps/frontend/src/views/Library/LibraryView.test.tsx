import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { LibraryView, type VoiceSearchCommand } from './LibraryView';
import * as api from '../../services/api';

// Mock the API module
vi.mock('../../services/api', () => ({
  getMediaFiles: vi.fn(),
  searchMediaFiles: vi.fn(),
  semanticSearchMedia: vi.fn(),
  getMediaItem: vi.fn(),
  playMedia: vi.fn(),
  formatDuration: (seconds: number) => `${Math.floor(seconds / 60).toString()}:${(seconds % 60).toString()}`,
  formatFileSize: (bytes: number) => `${bytes.toString()} B`,
}));

describe('LibraryView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    vi.mocked(api.semanticSearchMedia).mockResolvedValue({ count: 0, latency_ms: 0, results: [] });
  });

  it('renders loading state initially', () => {
    vi.mocked(api.getMediaFiles).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );
    render(<LibraryView />);
    expect(screen.getByText('Loading media library...')).toBeDefined();
  });

  it('renders media grid after loading', async () => {
    const mockMedia = [
      {
        id: 1,
        file_path: '/media/movie.mp4',
        file_name: 'movie.mp4',
        file_size: 1000000,
        media_type: 'video' as const,
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        indexed_at: '2024-01-01T00:00:00Z',
        play_count: 0,
        resume_position_seconds: 0,
      },
    ];

    vi.mocked(api.getMediaFiles).mockResolvedValue(mockMedia);

    render(<LibraryView />);

    await waitFor(() => {
      expect(screen.getByText('Media Library')).toBeDefined();
    });
  });

  it('displays error message on load failure', async () => {
    vi.mocked(api.getMediaFiles).mockRejectedValue(
      new Error('Network error')
    );

    render(<LibraryView />);

    await waitFor(() => {
      expect(screen.getByText('Error Loading Media')).toBeDefined();
    });
  });

  it('applies voice query search when provided', async () => {
    const voiceCommand: VoiceSearchCommand = { id: 123, text: 'Play jazz music ' };
    const handleVoiceHandled = vi.fn();

    vi.mocked(api.getMediaFiles).mockResolvedValue([]);
    vi.mocked(api.searchMediaFiles).mockResolvedValue([]);
    vi.mocked(api.semanticSearchMedia).mockResolvedValue({ count: 0, latency_ms: 0, results: [] });

    render(
      <LibraryView
        voiceQuery={voiceCommand}
        onVoiceQueryHandled={handleVoiceHandled}
      />
    );

    await waitFor(() => {
      expect(api.searchMediaFiles).toHaveBeenCalledWith('Play jazz music');
    });

    await waitFor(() => {
      expect(api.semanticSearchMedia).toHaveBeenCalledWith('Play jazz music', 12);
    });

    await waitFor(() => {
      expect(handleVoiceHandled).toHaveBeenCalledTimes(1);
    });

    await waitFor(() => {
      const input = screen.getByRole('textbox');
      expect(input.value).toBe('Play jazz music');
    });
  });

  it('merges semantic suggestions with text results', async () => {
    const mockMedia = [
      {
        id: 1,
        file_path: '/media/movie.mp4',
        file_name: 'movie.mp4',
        file_size: 1000000,
        media_type: 'video' as const,
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        indexed_at: '2024-01-01T00:00:00Z',
        play_count: 0,
        resume_position_seconds: 0,
      },
      {
        id: 2,
        file_path: '/media/song.mp3',
        file_name: 'song.mp3',
        file_size: 2048,
        media_type: 'audio' as const,
        created_at: '2024-01-02T00:00:00Z',
        modified_at: '2024-01-02T00:00:00Z',
        indexed_at: '2024-01-02T00:00:00Z',
        play_count: 2,
        resume_position_seconds: 0,
      },
    ];

    vi.mocked(api.getMediaFiles).mockResolvedValue(mockMedia);
    const [firstResult] = mockMedia;
    if (!firstResult) {
      throw new Error('Expected at least one media item in mock data');
    }
    vi.mocked(api.searchMediaFiles).mockResolvedValue([firstResult]);
    vi.mocked(api.semanticSearchMedia).mockResolvedValue({
      count: 2,
      latency_ms: 42,
      results: [
        { media_id: 1, title: 'movie', media_type: 'video', score: 0.95, document: null, metadata: {} },
        {
          media_id: 2,
          title: 'song',
          media_type: 'audio',
          score: 0.82,
          document: null,
          metadata: {
            media_id: 2,
            file_name: 'song.mp3',
            file_path: '/media/song.mp3',
            media_type: 'audio',
            created_at: '2024-01-02T00:00:00Z',
            modified_at: '2024-01-02T00:00:00Z',
            indexed_at: '2024-01-02T00:00:00Z',
          },
        },
      ],
    });

    render(<LibraryView />);

    await waitFor(() => {
      expect(screen.getByText('Media Library')).toBeDefined();
    });

    const textBox = screen.getByRole('textbox');
    fireEvent.change(textBox, { target: { value: 'mo' } });

    await waitFor(() => {
      expect(api.searchMediaFiles).toHaveBeenCalledWith('mo');
      expect(api.semanticSearchMedia).toHaveBeenCalledWith('mo', 12);
    });

    await waitFor(() => {
      expect(screen.getByText('Semantic + text match')).toBeDefined();
      expect(screen.getByText('Semantic suggestion')).toBeDefined();
    });

    await waitFor(() => {
      expect(screen.getByText(/Semantic boost added 1 match/)).toBeDefined();
    });
  });
});
