import React, { useState, useEffect, useRef } from 'react';
import './VoiceButton.css';

interface VoiceButtonProps {
  onTranscript?: (text: string) => void;
  onError?: (error: string) => void;
  sessionId?: string;
}

export const VoiceButton: React.FC<VoiceButtonProps> = ({
  onTranscript,
  onError,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      // Cleanup on unmount
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      setError(null);
      setTranscript('');

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        }
      });

      // Setup audio level monitoring
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      const source = audioContextRef.current.createMediaStreamSource(stream);
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;
      source.connect(analyserRef.current);

      // Start audio level monitoring
      monitorAudioLevel();

      // Setup MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        void processAudio();
        stream.getTracks().forEach(track => {
          track.stop();
        });
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to access microphone';
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);

      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        void audioContextRef.current.close();
      }
    }
  };

  const monitorAudioLevel = () => {
    if (!analyserRef.current) return;

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    
    const updateLevel = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      const normalized = Math.min(average / 128, 1);
      setAudioLevel(normalized);

      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };

    updateLevel();
  };

  const processAudio = async () => {
    setIsProcessing(true);

    try {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      
      // Convert to WAV format using AudioContext
      const audioBuffer = await audioBlob.arrayBuffer();
      const audioContext = new AudioContext({ sampleRate: 16000 });
      const decodedAudio = await audioContext.decodeAudioData(audioBuffer);

      // Convert to 16-bit PCM WAV
      const wavBlob = audioBufferToWav(decodedAudio);
      
      // Convert to base64
      const reader = new FileReader();
      reader.readAsDataURL(wavBlob);
      
      reader.onloadend = async () => {
        const base64Audio = reader.result as string;
        const base64Data = base64Audio.split(',')[1];

        // Send to STT endpoint
        const response = await fetch('http://localhost:8000/v1/voice/stt', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            audio_data: base64Data
          })
        });

        if (!response.ok) {
          throw new Error(`Transcription failed: ${response.statusText}`);
        }

        interface STTResponse {
          text: string;
        }

        const result = await response.json() as STTResponse;
        setTranscript(result.text);
        
        if (onTranscript) {
          onTranscript(result.text);
        }
      };

      await audioContext.close();

    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to process audio';
      setError(errorMsg);
      if (onError) {
        onError(errorMsg);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const audioBufferToWav = (audioBuffer: AudioBuffer): Blob => {
    const numberOfChannels = 1; // Mono
    const sampleRate = 16000;
    const format = 1; // PCM
    const bitDepth = 16;

    const samples = audioBuffer.getChannelData(0);
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    // WAV header
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true); // fmt chunk size
    view.setUint16(20, format, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * bitDepth / 8, true);
    view.setUint16(32, numberOfChannels * bitDepth / 8, true);
    view.setUint16(34, bitDepth, true);
    writeString(36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++) {
      const rawSample = samples[i];
      if (rawSample !== undefined) {
        const sample = Math.max(-1, Math.min(1, rawSample));
        view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      }
      offset += 2;
    }

    return new Blob([buffer], { type: 'audio/wav' });
  };

  const handleMouseDown = () => {
    if (!isRecording && !isProcessing) {
      void startRecording();
    }
  };

  const handleMouseUp = () => {
    if (isRecording) {
      stopRecording();
    }
  };

  return (
    <div className="voice-button-container">
      <button
        className={`voice-button ${isRecording ? 'recording' : ''} ${isProcessing ? 'processing' : ''}`}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleMouseDown}
        onTouchEnd={handleMouseUp}
        disabled={isProcessing}
        aria-label="Push to talk"
      >
        <div className="voice-button-icon">
          {isProcessing ? (
            <div className="spinner" />
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
              <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
            </svg>
          )}
        </div>
        
        {isRecording && (
          <div className="audio-level-indicator">
            <div 
              className="audio-level-bar" 
              style={{ width: `${(audioLevel * 100).toFixed(1)}%` }}
            />
          </div>
        )}
      </button>

      <div className="voice-status">
        {isRecording && <span className="status-text">Recording...</span>}
        {isProcessing && <span className="status-text">Processing...</span>}
        {transcript && !isProcessing && (
          <div className="transcript-text">{transcript}</div>
        )}
        {error && <div className="error-text">{error}</div>}
      </div>

      {!isRecording && !isProcessing && !transcript && (
        <div className="voice-hint">Press and hold to speak</div>
      )}
    </div>
  );
};
