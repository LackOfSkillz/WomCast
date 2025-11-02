import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { LibraryView } from './LibraryView';
import * as api from '../../services/api';

// Mock the API module
vi.mock('../../services/api', () => ({
  getMediaFiles: vi.fn(),
  searchMediaFiles: vi.fn(),
  getMediaItem: vi.fn(),
  playMedia: vi.fn(),
  formatDuration: (seconds: number) => `${Math.floor(seconds / 60).toString()}:${(seconds % 60).toString()}`,
  formatFileSize: (bytes: number) => `${bytes.toString()} B`,
}));

describe('LibraryView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
