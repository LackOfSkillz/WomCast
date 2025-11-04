interface FetchRetryOptions {
  retries?: number;
  backoffMs?: number;
  retryStatus?: number[];
  serviceName?: string;
}

const DEFAULT_RETRY_STATUS = [408, 425, 429, 500, 502, 503, 504];

const delay = (ms: number) => new Promise((resolve) => {
  setTimeout(resolve, ms);
});

/**
 * Minimal retry wrapper for fetch that backs off on transient failures.
 */
export async function fetchWithRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
  options?: FetchRetryOptions,
): Promise<Response> {
  const { retries = 2, backoffMs = 400, retryStatus = DEFAULT_RETRY_STATUS, serviceName } = options ?? {};

  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(input, init);

      if (!response.ok && retryStatus.includes(response.status) && attempt < retries) {
        await delay(backoffMs * 2 ** attempt);
        continue;
      }

      return response;
    } catch (error) {
      const isLastAttempt = attempt >= retries;
      const isNetworkError = error instanceof TypeError;

      if (!isNetworkError || isLastAttempt) {
        const details = error instanceof Error ? error.message : 'Unknown error';
        throw new Error(`${serviceName ?? 'Request'} failed: ${details}`);
      }

      await delay(backoffMs * 2 ** attempt);
    }
  }

  throw new Error(`${serviceName ?? 'Request'} failed after retries.`);
}
