"""
agentops.integrations.openai_patch
====================================
Monkey-patches the ``openai`` Python SDK so every ``chat.completions.create``
and ``AsyncOpenAI.chat.completions.create`` call is automatically captured as
an AgentOps span.

Usage
-----
::

    import openai
    import agentops
    from agentops.integrations.openai_patch import patch_openai, unpatch_openai

    agentops.init(api_key="ao_live_xxx")
    patch_openai()

    client = openai.OpenAI(api_key="sk-...")
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}],
    )
    # → an AgentOps span is automatically created with token usage

    unpatch_openai()   # restore original behaviour

Requirements
------------
::

    pip install "agentops-sdk[openai]"

Thread / async safety
---------------------
``patch_openai`` and ``unpatch_openai`` are **not** thread-safe with respect
to each other.  Call them from the main thread before spawning workers.

The patched sync wrapper is thread-safe.  The async wrapper is safe to use
with any event loop.

.. warning::
   Only patches ``openai.chat.completions.create`` (the most common path).
   Image generation, embeddings, etc. are **not** patched by this module.
   Open a PR or file an issue if you need broader coverage.
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Optional

from agentops.context import get_current_trace

logger = logging.getLogger(__name__)

try:
    import openai
    from openai import AsyncOpenAI, OpenAI
    from openai.resources.chat import AsyncCompletions, Completions
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The OpenAI integration requires the openai package. "
        "Run: pip install 'agentops-sdk[openai]'"
    ) from exc


# ---------------------------------------------------------------------------
# Module-level state: original references saved during patch_openai()
# ---------------------------------------------------------------------------
_original_sync_create: Optional[Any] = None
_original_async_create: Optional[Any] = None
_is_patched: bool = False


def patch_openai() -> None:
    """
    Monkey-patch ``openai.chat.completions.create`` (sync and async) so every
    call automatically creates an AgentOps span with:

    - Input messages (serialised to string).
    - Output text (first choice message content).
    - Model name, input tokens, output tokens, and estimated cost.

    The span is attached to the **currently active** trace context in the
    thread/task.  If there is no active trace, the span data is silently
    discarded (the original API call still executes normally).

    This function is idempotent — calling it multiple times has no additional
    effect.

    Example
    -------
    >>> from agentops.integrations.openai_patch import patch_openai
    >>> patch_openai()
    """
    global _original_sync_create, _original_async_create, _is_patched

    if _is_patched:
        logger.debug("patch_openai() called but openai is already patched; skipping.")
        return

    _original_sync_create = Completions.create
    _original_async_create = AsyncCompletions.create

    # ------------------------------------------------------------------
    # Synchronous patch
    # ------------------------------------------------------------------
    @functools.wraps(_original_sync_create)
    def _patched_sync_create(self_completions: Completions, *args: Any, **kwargs: Any) -> Any:
        ctx = get_current_trace()
        model = kwargs.get("model", args[0] if args else "unknown")
        messages = kwargs.get("messages", [])

        # Stringify messages for input recording
        input_text = _format_messages(messages)

        if ctx is not None:
            span = ctx.add_span(f"openai:chat.completions:{model}", span_type="llm")
            span.__enter__()
            span.set_input(input_text)
            span.set_metadata("model", model)
            exc_info = (None, None, None)
            try:
                response = _original_sync_create(self_completions, *args, **kwargs)
                _populate_span_from_response(span, response, model)
                return response
            except Exception as exc:
                exc_info = (type(exc), exc, None)
                raise
            finally:
                span.__exit__(*exc_info)
        else:
            # No active trace — call through without instrumentation.
            return _original_sync_create(self_completions, *args, **kwargs)

    # ------------------------------------------------------------------
    # Asynchronous patch
    # ------------------------------------------------------------------
    @functools.wraps(_original_async_create)
    async def _patched_async_create(self_completions: AsyncCompletions, *args: Any, **kwargs: Any) -> Any:
        ctx = get_current_trace()
        model = kwargs.get("model", args[0] if args else "unknown")
        messages = kwargs.get("messages", [])
        input_text = _format_messages(messages)

        if ctx is not None:
            span = ctx.add_span(f"openai:chat.completions:{model}", span_type="llm")
            span.__enter__()
            span.set_input(input_text)
            span.set_metadata("model", model)
            exc_info = (None, None, None)
            try:
                response = await _original_async_create(self_completions, *args, **kwargs)
                _populate_span_from_response(span, response, model)
                return response
            except Exception as exc:
                exc_info = (type(exc), exc, None)
                raise
            finally:
                span.__exit__(*exc_info)
        else:
            return await _original_async_create(self_completions, *args, **kwargs)

    # Apply the patches at the class level so all client instances are affected.
    Completions.create = _patched_sync_create  # type: ignore[method-assign]
    AsyncCompletions.create = _patched_async_create  # type: ignore[method-assign]

    _is_patched = True
    logger.debug("openai.chat.completions.create patched for AgentOps tracing.")


def unpatch_openai() -> None:
    """
    Restore the original ``openai.chat.completions.create`` methods.

    Safe to call even if ``patch_openai()`` has not been called (no-op).

    Example
    -------
    >>> from agentops.integrations.openai_patch import unpatch_openai
    >>> unpatch_openai()
    """
    global _original_sync_create, _original_async_create, _is_patched

    if not _is_patched:
        logger.debug("unpatch_openai() called but openai was not patched; skipping.")
        return

    if _original_sync_create is not None:
        Completions.create = _original_sync_create  # type: ignore[method-assign]
        _original_sync_create = None

    if _original_async_create is not None:
        AsyncCompletions.create = _original_async_create  # type: ignore[method-assign]
        _original_async_create = None

    _is_patched = False
    logger.debug("openai.chat.completions.create restored to original.")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _format_messages(messages: Any) -> str:
    """Convert a list of message dicts to a readable string for span input."""
    if not messages:
        return ""
    parts = []
    for msg in messages:
        role = msg.get("role", "?") if isinstance(msg, dict) else getattr(msg, "role", "?")
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def _populate_span_from_response(span: Any, response: Any, model: str) -> None:
    """
    Extract output text and token usage from an ``openai.ChatCompletion`` response
    and populate the span accordingly.
    """
    try:
        output_text = response.choices[0].message.content or ""
    except (AttributeError, IndexError):
        output_text = ""

    span.set_output(output_text)

    # Extract token usage from the response object.
    try:
        usage = response.usage
        if usage:
            tokens_in = getattr(usage, "prompt_tokens", 0) or 0
            tokens_out = getattr(usage, "completion_tokens", 0) or 0
            # Use the model from the response (may differ from the requested model).
            actual_model = getattr(response, "model", model) or model
            span.set_model(actual_model, tokens_input=tokens_in, tokens_output=tokens_out)
    except AttributeError:
        pass
