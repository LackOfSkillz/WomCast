import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { CloudBadge } from './CloudBadge';

// Mock fetch
global.fetch = vi.fn();

const mockService = {
  provider: 'netflix',
  name: 'Netflix',
  description: 'Stream movies, TV shows, and originals',
  iconUrl: 'https://example.com/netflix.png',
  requiresSubscription: true,
  regions: ['US', 'CA', 'GB'],
};

describe('CloudBadge', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders service information correctly', () => {
    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
      />
    );

    expect(screen.getByText('Netflix')).toBeInTheDocument();
    expect(
      screen.getByText('Stream movies, TV shows, and originals')
    ).toBeInTheDocument();
    expect(screen.getByText('⭐ Subscription')).toBeInTheDocument();
  });

  it('shows subscription badge only when required', () => {
    const freeService = { ...mockService, requiresSubscription: false };

    render(
      <CloudBadge
        service={freeService}
        contentId="test-id"
        contentTitle="Test Content"
      />
    );

    expect(screen.queryByText('⭐ Subscription')).not.toBeInTheDocument();
  });

  it('displays service icon', () => {
    render(
      <CloudBadge
        service={mockService}
        contentId="test-id"
        contentTitle="Test Content"
      />
    );

    const icon = screen.getByAltText('Netflix');
    expect(icon).toHaveAttribute('src', 'https://example.com/netflix.png');
  });

  it('has both QR and web buttons', () => {
    render(
      <CloudBadge
        service={mockService}
        contentId="test-id"
        contentTitle="Test Content"
      />
    );

    expect(screen.getByText('📱 Scan QR')).toBeInTheDocument();
    expect(screen.getByText('🌐 Open in Browser')).toBeInTheDocument();
  });

  it('opens QR modal when scan button clicked', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        provider: 'netflix',
        title: 'Stranger Things',
        contentId: '80057281',
        deepLink: 'netflix://title/80057281',
        webLink: 'https://www.netflix.com/title/80057281',
        qrCodeUrl: '/v1/cloud/qr?provider=netflix&content_id=80057281',
      }),
    });

    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
      />
    );

    const scanButton = screen.getByText('📱 Scan QR');
    fireEvent.click(scanButton);

    await waitFor(() => {
      expect(
        screen.getByText('Scan to Watch on Netflix')
      ).toBeInTheDocument();
    });

    expect(
      screen.getByText(/Scan this code with your mobile device/)
    ).toBeInTheDocument();
  });

  it('calls onWatchClick callback when provided', async () => {
    const onWatchClick = vi.fn();

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        qrCodeUrl: '/v1/cloud/qr?provider=netflix&content_id=80057281',
      }),
    });

    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
        onWatchClick={onWatchClick}
      />
    );

    const scanButton = screen.getByText('📱 Scan QR');
    fireEvent.click(scanButton);

    await waitFor(() => {
      expect(onWatchClick).toHaveBeenCalledWith('netflix', '80057281');
    });
  });

  it('opens web link in new tab', async () => {
    const mockOpen = vi.fn();
    global.window.open = mockOpen;

    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        webLink: 'https://www.netflix.com/title/80057281',
      }),
    });

    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
      />
    );

    const webButton = screen.getByText('🌐 Open in Browser');
    fireEvent.click(webButton);

    await waitFor(() => {
      expect(mockOpen).toHaveBeenCalledWith(
        'https://www.netflix.com/title/80057281',
        '_blank'
      );
    });
  });

  it('closes QR modal when close button clicked', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        qrCodeUrl: '/v1/cloud/qr?provider=netflix&content_id=80057281',
      }),
    });

    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
      />
    );

    // Open modal
    const scanButton = screen.getByText('📱 Scan QR');
    fireEvent.click(scanButton);

    await waitFor(() => {
      expect(
        screen.getByText('Scan to Watch on Netflix')
      ).toBeInTheDocument();
    });

    // Close modal
    const closeButton = screen.getByText('Close');
    fireEvent.click(closeButton);

    await waitFor(() => {
      expect(
        screen.queryByText('Scan to Watch on Netflix')
      ).not.toBeInTheDocument();
    });
  });

  it('displays subscription note in QR modal for paid services', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        qrCodeUrl: '/v1/cloud/qr?provider=netflix&content_id=80057281',
      }),
    });

    render(
      <CloudBadge
        service={mockService}
        contentId="80057281"
        contentTitle="Stranger Things"
      />
    );

    const scanButton = screen.getByText('📱 Scan QR');
    fireEvent.click(scanButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Active Netflix subscription required/)
      ).toBeInTheDocument();
    });
  });
});
