import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { VoiceButton } from './VoiceButton';

describe('VoiceButton', () => {
  let mockMediaRecorder: {
    start: ReturnType<typeof vi.fn>;
    stop: ReturnType<typeof vi.fn>;
    ondataavailable: ((event: BlobEvent) => void) | null;
    onstop: (() => void) | null;
  };

  let mockAudioContext: {
    createMediaStreamSource: ReturnType<typeof vi.fn>;
    createAnalyser: ReturnType<typeof vi.fn>;
    decodeAudioData: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
  };

  let mockAnalyser: {
    connect: ReturnType<typeof vi.fn>;
    getByteFrequencyData: ReturnType<typeof vi.fn>;
    fftSize: number;
  };

  let mockStream: {
    getTracks: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    // Mock MediaRecorder
    mockMediaRecorder = {
      start: vi.fn(),
      stop: vi.fn(),
      ondataavailable: null,
      onstop: null,
    };

    global.MediaRecorder = vi.fn(() => mockMediaRecorder) as unknown as typeof MediaRecorder;

    // Mock AudioContext
    mockAnalyser = {
      connect: vi.fn(),
      getByteFrequencyData: vi.fn((arr: Uint8Array) => {
        // Simulate some audio data
        for (let i = 0; i < arr.length; i++) {
          arr[i] = Math.random() * 128;
        }
      }),
      fftSize: 256,
    };

    mockAudioContext = {
      createMediaStreamSource: vi.fn(() => ({ connect: vi.fn() })),
      createAnalyser: vi.fn(() => mockAnalyser),
      decodeAudioData: vi.fn(async () => ({
        getChannelData: () => new Float32Array(16000),
        numberOfChannels: 1,
        sampleRate: 16000,
        length: 16000,
        duration: 1,
      })),
      close: vi.fn(async () => undefined),
    };

    global.AudioContext = vi.fn(() => mockAudioContext) as unknown as typeof AudioContext;

    // Mock getUserMedia
    mockStream = {
      getTracks: vi.fn(() => [{ stop: vi.fn() }]),
    };

    global.navigator.mediaDevices = {
      getUserMedia: vi.fn(async () => mockStream),
    } as unknown as MediaDevices;

    // Mock FileReader
    class MockFileReader {
      result: string | null = null;
      onloadend: (() => void) | null = null;

      readAsDataURL() {
        // Simulate base64 audio data
        this.result = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=';
        if (this.onloadend) {
          setTimeout(() => {
            if (this.onloadend) {
              this.onloadend();
            }
          }, 0);
        }
      }
    }

    global.FileReader = MockFileReader as unknown as typeof FileReader;

    // Mock fetch
    global.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({ text: 'test transcription' }),
      statusText: 'OK',
    })) as unknown as typeof fetch;

    // Mock requestAnimationFrame
    global.requestAnimationFrame = vi.fn((cb) => {
      setTimeout(cb, 0);
      return 0;
    });

    global.cancelAnimationFrame = vi.fn();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the voice button', () => {
    render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');
    expect(button).toBeDefined();
  });

  it('starts recording on mouse down', async () => {
    render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);

    await waitFor(() => {
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    });

    await waitFor(() => {
      expect(mockMediaRecorder.start).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Recording...')).toBeDefined();
    });
  });

  it('stops recording on mouse up', async () => {
    render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    fireEvent.mouseUp(button);
    await waitFor(() => {
      expect(mockMediaRecorder.stop).toHaveBeenCalled();
    });
  });

  it('processes audio and calls STT endpoint after recording', async () => {
    render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    // Simulate data available
    const audioBlob = new Blob(['test audio'], { type: 'audio/webm' });
    if (mockMediaRecorder.ondataavailable) {
      mockMediaRecorder.ondataavailable(new BlobEvent('dataavailable', { data: audioBlob }));
    }

    fireEvent.mouseUp(button);
    await waitFor(() => expect(mockMediaRecorder.stop).toHaveBeenCalled());

    // Trigger onstop callback
    if (mockMediaRecorder.onstop) {
      mockMediaRecorder.onstop();
    }

    await waitFor(() => {
      expect(screen.getByText('Processing...')).toBeDefined();
    }, { timeout: 2000 });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        'http://localhost:8000/v1/voice/stt',
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        })
      );
    }, { timeout: 2000 });
  });

  it('calls onTranscript callback with result', async () => {
    const onTranscript = vi.fn();
    render(<VoiceButton onTranscript={onTranscript} />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    const audioBlob = new Blob(['test audio'], { type: 'audio/webm' });
    if (mockMediaRecorder.ondataavailable) {
      mockMediaRecorder.ondataavailable(new BlobEvent('dataavailable', { data: audioBlob }));
    }

    fireEvent.mouseUp(button);
    if (mockMediaRecorder.onstop) {
      mockMediaRecorder.onstop();
    }

    await waitFor(() => {
      expect(onTranscript).toHaveBeenCalledWith('test transcription');
    }, { timeout: 3000 });
  });

  it('handles microphone access error', async () => {
    const onError = vi.fn();
    (navigator.mediaDevices.getUserMedia as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('Permission denied')
    );

    render(<VoiceButton onError={onError} />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Permission denied');
    });

    await waitFor(() => {
      expect(screen.getByText('Permission denied')).toBeDefined();
    });
  });

  it('handles transcription API error', async () => {
    const onError = vi.fn();
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      statusText: 'Internal Server Error',
    });

    render(<VoiceButton onError={onError} />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    const audioBlob = new Blob(['test audio'], { type: 'audio/webm' });
    if (mockMediaRecorder.ondataavailable) {
      mockMediaRecorder.ondataavailable(new BlobEvent('dataavailable', { data: audioBlob }));
    }

    fireEvent.mouseUp(button);
    if (mockMediaRecorder.onstop) {
      mockMediaRecorder.onstop();
    }

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith(expect.stringContaining('Transcription failed'));
    }, { timeout: 3000 });
  });

  it('prevents recording when already recording', async () => {
    render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    const startCallCount = mockMediaRecorder.start.mock.calls.length;

    // Try to start again
    fireEvent.mouseDown(button);

    // Should not start again
    expect(mockMediaRecorder.start).toHaveBeenCalledTimes(startCallCount);
  });

  it('cleans up resources on unmount', async () => {
    const { unmount } = render(<VoiceButton />);
    const button = screen.getByLabelText('Push to talk');

    fireEvent.mouseDown(button);
    await waitFor(() => expect(mockMediaRecorder.start).toHaveBeenCalled());

    unmount();

    // Close should be called on unmount
    await waitFor(() => {
      expect(mockAudioContext.close).toHaveBeenCalled();
    });
  });
});
