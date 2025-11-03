"""
WomCast Connector Resilience Module
Provides retry logic, rate limiting, and circuit breaker patterns for external API connectors.

This module ensures connectors fail gracefully and respect API rate limits.
"""

import asyncio
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failure threshold reached, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""

    failure_threshold: int = 5  # Open circuit after N failures
    success_threshold: int = 2  # Close circuit after N successes
    timeout: float = 30.0  # Seconds to wait before half-open

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    success_count: int = field(default=0, init=False)
    last_failure_time: float | None = field(default=None, init=False)

    def record_success(self) -> None:
        """Record successful request."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self.state = CircuitState.CLOSED
                self.success_count = 0

    def record_failure(self) -> None:
        """Record failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if request can proceed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout elapsed
            if (
                self.last_failure_time
                and time.time() - self.last_failure_time >= self.timeout
            ):
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        # HALF_OPEN: allow one request to test
        return True


@dataclass
class RateLimiter:
    """Token bucket rate limiter."""

    max_requests: int  # Maximum requests per interval
    interval: float  # Time interval in seconds

    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self) -> None:
        """Initialize token bucket."""
        self.tokens = float(self.max_requests)
        self.last_update = time.time()

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        now = time.time()
        elapsed = now - self.last_update

        # Refill tokens based on elapsed time
        self.tokens = min(
            float(self.max_requests), self.tokens + (elapsed / self.interval) * self.max_requests
        )
        self.last_update = now

        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    async def wait(self) -> None:
        """Wait until a token is available."""
        while not self.acquire():
            # Calculate wait time until next token
            wait_time = (1.0 - self.tokens) * self.interval / self.max_requests
            await asyncio.sleep(max(0.01, wait_time))


class RetryConfig:
    """Configuration for exponential backoff retry."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
    ):
        """
        Initialize retry configuration.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff calculation
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


async def retry_with_backoff(
    func: Callable[[], Coroutine[Any, Any, T]],
    config: RetryConfig,
    circuit_breaker: CircuitBreaker | None = None,
) -> T:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        config: Retry configuration
        circuit_breaker: Optional circuit breaker

    Returns:
        Function result

    Raises:
        Exception: Last exception if all retries failed
    """
    last_exception: Exception | None = None

    for attempt in range(config.max_attempts):
        # Check circuit breaker
        if circuit_breaker and not circuit_breaker.can_execute():
            raise Exception("Circuit breaker is OPEN")

        try:
            result = await func()
            if circuit_breaker:
                circuit_breaker.record_success()
            return result
        except Exception as e:
            last_exception = e
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Don't sleep after last attempt
            if attempt < config.max_attempts - 1:
                delay = config.get_delay(attempt)
                await asyncio.sleep(delay)

    # All retries exhausted
    if last_exception:
        raise last_exception
    raise Exception("All retry attempts failed")


# Global rate limiters for connectors
RATE_LIMITERS: dict[str, RateLimiter] = {
    "internet_archive": RateLimiter(max_requests=1, interval=1.0),  # 1 req/s
    "pbs": RateLimiter(max_requests=2, interval=1.0),  # 2 req/s
    "nasa": RateLimiter(max_requests=2, interval=1.0),  # 2 req/s
    "jamendo": RateLimiter(max_requests=2, interval=1.0),  # 2 req/s
}

# Global circuit breakers for connectors
CIRCUIT_BREAKERS: dict[str, CircuitBreaker] = {
    "internet_archive": CircuitBreaker(),
    "pbs": CircuitBreaker(),
    "nasa": CircuitBreaker(),
    "jamendo": CircuitBreaker(),
}


async def with_resilience(
    connector_name: str,
    func: Callable[[], Coroutine[Any, Any, T]],
    retry_config: RetryConfig | None = None,
) -> T:
    """
    Execute connector function with rate limiting, retry, and circuit breaker.

    Args:
        connector_name: Name of connector for rate limiting/circuit breaking
        func: Async function to execute
        retry_config: Optional retry configuration (default: 3 attempts)

    Returns:
        Function result

    Raises:
        Exception: If all retries failed or circuit breaker is open
    """
    # Rate limiting
    rate_limiter = RATE_LIMITERS.get(connector_name)
    if rate_limiter:
        await rate_limiter.wait()

    # Retry with circuit breaker
    circuit_breaker = CIRCUIT_BREAKERS.get(connector_name)
    config = retry_config or RetryConfig(max_attempts=3)

    return await retry_with_backoff(func, config, circuit_breaker)


# CLI for testing
if __name__ == "__main__":

    async def test_rate_limiter():
        """Test rate limiter."""
        limiter = RateLimiter(max_requests=2, interval=1.0)
        print("Testing rate limiter (2 req/s):")
        for i in range(5):
            start = time.time()
            await limiter.wait()
            elapsed = time.time() - start
            print(f"  Request {i + 1}: {elapsed:.3f}s wait")

    async def test_circuit_breaker():
        """Test circuit breaker."""
        breaker = CircuitBreaker(failure_threshold=3, timeout=2.0)
        print("\nTesting circuit breaker:")

        # Simulate failures
        for i in range(5):
            breaker.record_failure()
            print(f"  Failure {i + 1}: state={breaker.state.value}")

        # Try to execute (should fail)
        print(f"  Can execute? {breaker.can_execute()}")

        # Wait for timeout
        print("  Waiting 2s for timeout...")
        await asyncio.sleep(2.0)
        print(f"  Can execute? {breaker.can_execute()} (state={breaker.state.value})")

        # Simulate success
        breaker.record_success()
        breaker.record_success()
        print(f"  After 2 successes: state={breaker.state.value}")

    async def test_retry():
        """Test retry with backoff."""
        print("\nTesting exponential backoff:")
        config = RetryConfig(max_attempts=4, base_delay=0.5)

        attempt = [0]

        async def flaky_function() -> str:
            attempt[0] += 1
            print(f"  Attempt {attempt[0]}")
            if attempt[0] < 3:
                raise Exception("Simulated failure")
            return "Success!"

        try:
            result = await retry_with_backoff(flaky_function, config)
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  Failed: {e}")

    async def main():
        """Run all tests."""
        await test_rate_limiter()
        await test_circuit_breaker()
        await test_retry()

    asyncio.run(main())
