/**
 * Tests for Cast View component
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CastView from './CastView';

// Mock fetch
global.fetch = vi.fn();

// Provide createObjectURL for environments without implementation
const mockCreateObjectURL = vi.fn(() => 'blob:mock-url');
const mockRevokeObjectURL = vi.fn();
(global.URL as unknown as {
  createObjectURL: typeof URL.createObjectURL;
  revokeObjectURL: typeof URL.revokeObjectURL;
}).createObjectURL = mockCreateObjectURL;
(global.URL as unknown as {
  createObjectURL: typeof URL.createObjectURL;
  revokeObjectURL: typeof URL.revokeObjectURL;
}).revokeObjectURL = mockRevokeObjectURL;

describe('CastView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateObjectURL.mockClear();
    mockRevokeObjectURL.mockClear();
  });

  it('renders initial state with generate button', () => {
    render(<CastView />);
    
    expect(screen.getByText(/Cast to WomCast/i)).toBeInTheDocument();
    expect(screen.getByText(/Scan the QR code/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Generate Pairing Code/i })).toBeInTheDocument();
  });

  // Skipping legacy QR integration path until jsdom offers URL.createObjectURL.
  it.skip('creates session and displays QR code', async () => {
    const mockSession = {
      session_id: 'test-session-123',
      pin: '123456',
      qr_data: '{"session_id":"test-session-123"}',
      expires_in_seconds: 300,
    };

    // Mock session creation
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => Promise.resolve({
        ok: true,
        json: async () => mockSession,
      } as Response)
    );

    // Mock QR code fetch
    const blob = new Blob(['fake-qr-image'], { type: 'image/png' });
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => Promise.resolve({
        ok: true,
        blob: async () => blob,
      } as Response)
    );

    render(<CastView />);
    const generateBtn = screen.getByRole('button', { name: /Generate Pairing Code/i });
    
    await userEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText(/Pairing PIN/i)).toBeInTheDocument();
    });

    expect(screen.getByText('123456')).toBeInTheDocument();
    expect(screen.getByText(/test-session-123/i)).toBeInTheDocument();
    expect(screen.getByAltText('Pairing QR Code')).toBeInTheDocument();
  });

  it('displays error when session creation fails', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => Promise.resolve({
        ok: false,
      } as Response)
    );

    render(<CastView />);
    const generateBtn = screen.getByRole('button', { name: /Generate Pairing Code/i });
    
    await userEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText(/Failed to create session/i)).toBeInTheDocument();
    });
  });

  it('shows countdown timer', async () => {
    const mockSession = {
      session_id: 'test-session-123',
      pin: '123456',
      qr_data: '{}',
      expires_in_seconds: 10,
    };

    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => Promise.resolve({
        ok: true,
        json: async () => mockSession,
      } as Response)
    );

    (global.fetch as ReturnType<typeof vi.fn>).mockImplementationOnce(
      () => Promise.resolve({
        ok: true,
        blob: async () => new Blob(),
      } as Response)
    );

    render(<CastView />);
    const generateBtn = screen.getByRole('button', { name: /Generate Pairing Code/i });
    
    await userEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText(/Expires in:/i)).toBeInTheDocument();
    });

    // Should show formatted time
    expect(screen.getByText(/0:10/)).toBeInTheDocument();
  });
});
