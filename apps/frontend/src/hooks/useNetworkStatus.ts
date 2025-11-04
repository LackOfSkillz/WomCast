import { useEffect, useState } from 'react';

interface NetworkStatus {
  online: boolean;
  lastChangedAt: number;
}

/**
 * Track browser network availability so the UI can surface offline states.
 */
export function useNetworkStatus(): NetworkStatus {
  const [status, setStatus] = useState<NetworkStatus>(() => ({
    online: typeof navigator !== 'undefined' ? navigator.onLine : true,
    lastChangedAt: Date.now(),
  }));

  useEffect(() => {
    const handleOnline = () => {
      setStatus({ online: true, lastChangedAt: Date.now() });
    };

    const handleOffline = () => {
      setStatus({ online: false, lastChangedAt: Date.now() });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return status;
}
