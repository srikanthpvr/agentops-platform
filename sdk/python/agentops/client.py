"""
agentops.client
===============
HTTP transport layer for the AgentOps SDK.

``AgentOpsClient`` handles:
- Serialising and POSTing traces to the backend ingest API.
- Thread-safe batching with a background flush thread.
- Exponential-backoff retry on transient network failures.
- Graceful degradation: network errors are logged as warnings rather than
  raised, so a backend outage never crashes user code.

Thread-safety contract
----------------------
``_batch_queue`` is protected by ``_lock``.  The background flush thread
reads from and empties the queue under the same lock so there are no races
between the background flusher and foreground callers.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Dict, List, Optional

import httpx

from .models import SDKConfig, TraceData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pricing table (USD per 1 000 tokens)
# Used by the client to validate / supplement span cost estimates.
# The source of truth for cost calculation is agentops/span.py; this table
# is kept here for reference and future server-side reconciliation.
# ---------------------------------------------------------------------------
_MODEL_COST_PER_1K: Dict[str, Dict[str, float]] = {
    "gpt-4o":           {"input": 0.005,  "output": 0.015},
    "gpt-4o-mini":      {"input": 0.00015,"output": 0.0006},
    "gpt-4-turbo":      {"input": 0.01,   "output": 0.03},
    "gpt-4":            {"input": 0.03,   "output": 0.06},
    "gpt-3.5-turbo":    {"input": 0.0005, "output": 0.0015},
    "claude-3-5-sonnet":{"input": 0.003,  "output": 0.015},
    "claude-3-opus":    {"input": 0.015,  "output": 0.075},
    "claude-3-haiku":   {"input": 0.00025,"output": 0.00125},
    "gemini-1.5-pro":   {"input": 0.00125,"output": 0.005},
    "gemini-1.5-flash": {"input": 0.000075,"output":0.0003},
}


class AgentOpsClient:
    """
    Low-level HTTP client that ships traces to the AgentOps ingest API.

    Parameters
    ----------
    api_key:
        Your AgentOps API key.  Never log or expose this value.
    base_url:
        Root URL of the AgentOps API (default: ``https://api.agentops.io``).
    timeout:
        Per-request timeout in seconds.
    batch_size:
        How many traces to accumulate before an automatic flush.
    flush_interval:
        Seconds between background flush attempts.
    max_retries:
        Maximum retry attempts on transient failure (uses exponential back-off).
    debug:
        When True, the client logs at DEBUG level.

    Example
    -------
    >>> client = AgentOpsClient(api_key="ao_live_xxx")
    >>> client.enqueue(trace_data_dict)
    >>> client.flush()
    >>> client.close()
    """

    _INGEST_PATH = "/api/v1/ingest/traces"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.agentops.io",
        timeout: float = 30.0,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        max_retries: int = 3,
        debug: bool = False,
    ) -> None:
        self._config = SDKConfig(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            batch_size=batch_size,
            flush_interval=flush_interval,
            max_retries=max_retries,
            debug=debug,
        )

        if debug:
            logging.getLogger("agentops").setLevel(logging.DEBUG)

        # Build the shared httpx client with default headers.
        # The API key is passed per-request so we don't have to recreate the
        # client if the key is rotated via configure().
        self._http = httpx.Client(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": f"agentops-sdk/0.1.0",
            },
        )

        # Thread-safe batch queue
        self._batch_queue: List[dict] = []
        self._lock = threading.Lock()

        # Background flush thread — daemon so it doesn't block process exit.
        self._stop_event = threading.Event()
        self._flush_thread = threading.Thread(
            target=self._background_flush_loop,
            name="agentops-flush",
            daemon=True,
        )
        self._flush_thread.start()
        logger.debug("AgentOpsClient initialised; flush thread started.")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def api_key(self) -> str:
        return self._config.api_key

    def enqueue(self, trace_data: dict) -> None:
        """
        Add a trace payload to the batch queue.

        When the queue reaches ``batch_size``, an immediate flush is triggered.
        This method is non-blocking and thread-safe.

        Parameters
        ----------
        trace_data:
            Serialised :class:`~agentops.models.TraceData` dict ready for JSON encoding.
        """
        with self._lock:
            self._batch_queue.append(trace_data)
            should_flush = len(self._batch_queue) >= self._config.batch_size

        if should_flush:
            logger.debug("Batch size reached (%d); triggering immediate flush.", self._config.batch_size)
            self._flush_locked()

    def flush(self) -> None:
        """
        Force an immediate flush of all buffered traces to the backend.

        Blocks until the HTTP request completes (or all retries are exhausted).
        Safe to call from any thread.
        """
        self._flush_locked()

    def close(self) -> None:
        """
        Flush all remaining traces, stop the background thread, and close the HTTP client.

        Call this at process shutdown to ensure no traces are dropped.

        Example
        -------
        >>> import atexit
        >>> atexit.register(client.close)
        """
        logger.debug("AgentOpsClient.close() called; flushing remaining traces.")
        self._stop_event.set()
        self._flush_locked()          # final flush before closing HTTP client
        self._flush_thread.join(timeout=5.0)
        self._http.close()
        logger.debug("AgentOpsClient closed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _background_flush_loop(self) -> None:
        """
        Background thread target: flush the queue every ``flush_interval`` seconds
        until ``_stop_event`` is set.
        """
        while not self._stop_event.wait(timeout=self._config.flush_interval):
            self._flush_locked()

    def _flush_locked(self) -> None:
        """Drain the queue and send all buffered traces."""
        with self._lock:
            if not self._batch_queue:
                return
            # Snapshot and clear atomically under the lock.
            batch = list(self._batch_queue)
            self._batch_queue.clear()

        logger.debug("Flushing %d trace(s) to backend.", len(batch))
        for trace_payload in batch:
            try:
                self._send_trace(trace_payload)
            except Exception as exc:  # pragma: no cover — network or unexpected error
                # Log and continue; never crash user code due to observability failure.
                logger.warning(
                    "AgentOps: failed to send trace %s after retries: %s",
                    trace_payload.get("trace_id", "?"),
                    exc,
                )

    def _send_trace(self, trace_data: dict) -> dict:
        """
        POST a single trace payload to ``/api/v1/ingest/traces``.

        Implements exponential back-off retry (base 1 s, max ``max_retries``
        attempts) for transient HTTP errors (5xx, connection errors, timeouts).

        Parameters
        ----------
        trace_data:
            JSON-serialisable dict representing a :class:`~agentops.models.TraceData`.

        Returns
        -------
        dict
            Parsed JSON response body from the backend.

        Raises
        ------
        RuntimeError
            When all retry attempts are exhausted.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._config.max_retries + 1):
            try:
                response = self._http.post(
                    self._INGEST_PATH,
                    json=trace_data,
                    headers={"X-API-Key": self._config.api_key},
                )
                response.raise_for_status()
                logger.debug(
                    "Trace %s ingested (HTTP %d, attempt %d).",
                    trace_data.get("trace_id", "?"),
                    response.status_code,
                    attempt + 1,
                )
                return response.json() if response.content else {}

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.debug("Request timeout on attempt %d: %s", attempt + 1, exc)
            except httpx.NetworkError as exc:
                last_exc = exc
                logger.debug("Network error on attempt %d: %s", attempt + 1, exc)
            except httpx.HTTPStatusError as exc:
                # Retry on 5xx server errors; fail fast on 4xx client errors.
                if exc.response.status_code < 500:
                    logger.warning(
                        "AgentOps ingest returned client error %d for trace %s — not retrying.",
                        exc.response.status_code,
                        trace_data.get("trace_id", "?"),
                    )
                    raise
                last_exc = exc
                logger.debug("Server error %d on attempt %d.", exc.response.status_code, attempt + 1)

            if attempt < self._config.max_retries:
                # Exponential back-off: 1s, 2s, 4s, …
                sleep_time = 2 ** attempt
                logger.debug("Retrying in %.1fs…", sleep_time)
                time.sleep(sleep_time)

        raise RuntimeError(
            f"AgentOps: failed to send trace after {self._config.max_retries + 1} attempts. "
            f"Last error: {last_exc}"
        )

    @staticmethod
    def calculate_cost(model: str, tokens_input: int, tokens_output: int) -> Optional[float]:
        """
        Estimate the USD cost for an LLM call based on the global pricing table.

        Returns ``None`` if the model is not in the pricing table.

        Parameters
        ----------
        model:
            Model identifier string (e.g. ``"gpt-4o"``).
        tokens_input:
            Number of prompt/input tokens consumed.
        tokens_output:
            Number of completion/output tokens produced.

        Returns
        -------
        Optional[float]
            Estimated cost in USD, or None if the model is unknown.

        Example
        -------
        >>> AgentOpsClient.calculate_cost("gpt-4o", 1000, 500)
        0.012500000000000002
        """
        pricing = _MODEL_COST_PER_1K.get(model)
        if pricing is None:
            # Try prefix matching for versioned model names like "gpt-4o-2024-11-20"
            for key, prices in _MODEL_COST_PER_1K.items():
                if model.startswith(key):
                    pricing = prices
                    break
        if pricing is None:
            return None
        return (tokens_input / 1000) * pricing["input"] + (tokens_output / 1000) * pricing["output"]
