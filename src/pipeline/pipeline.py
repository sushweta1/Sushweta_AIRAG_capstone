"""W4 REFERENCE — src/pipeline/pipeline.py

Final shape after Lab Step 1 + Step 2:
  • ask_llm uses tool-calling for structured Answer outputs.
  • stream_answer uses real OpenAI streaming.
  • Both paths compute real cost_usd from response.usage via cost.py.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from openai import AsyncOpenAI

from .cost import compute_cost_usd
from .models import Answer, Question
from .settings import Settings

logger = logging.getLogger(__name__)
# Backward compatibility for W2/W3 tests.
_settings_for_import = Settings()


# ─── Tool schema for structured outputs ─────────────────────────────────────
ANSWER_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "answer_question",
        "description": (
            "Return a structured answer with content, confidence, and sources."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The answer in 2-4 sentences.",
                },
                "confidence": {
                    "type": "number",
                    "description": "How confident you are in the answer, 0.0 to 1.0.",
                },
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Source identifiers or URLs you used. Empty list is fine "
                        "if you used general knowledge."
                    ),
                },
            },
            "required": ["content", "confidence", "sources"],
        },
    },
}


# ─── Fake LLM (kept from W2 for tests) ──────────────────────────────────────
async def fake_ask_llm(question: str) -> str:
    """Returns a canned answer with a small delay. Used by tests + offline runs."""
    await asyncio.sleep(0.05)
    return f"[FAKE] {question[:60]}"


# ─── Real LLM call via tool-calling ─────────────────────────────────────────
async def ask_llm(
    q: Question,
    settings: Settings | None = None,
    system_prompt: str | None = None,
) -> Answer:
    """Call the LLM with tool-calling, returning a structured Answer.

    Retries on transient failures. Real cost computed from response.usage.
    """
    # W4 normally passes Settings explicitly.
    # Falling back to this shared object preserves the W2/W3 test contract.
    settings = settings or _settings_for_import

    # W4 Question uses .question; older W2/W3 Question used .text.
    question_text = getattr(q, "question", None)
    if question_text is None:
        question_text = getattr(q, "text")

    if settings.use_fake:
        fake_result = await fake_ask_llm(question_text)

        # Normal W4 fake implementation returns a string.
        if isinstance(fake_result, str):
            return Answer(
                content=fake_result,
                cost_usd=0.0,
                retries=0,
            )

        # Older W3 mocked tests return their original Answer object.
        return fake_result

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    last_err: Exception | None = None

    for attempt in range(settings.max_retries + 1):
        try:
            messages = []

            if system_prompt:
                messages.append(
                    {"role": "system", "content": system_prompt}
                )

            messages.append(
                {"role": "user", "content": question_text}
            )

            resp = await client.chat.completions.create(
                model=settings.model,
                messages=messages,
                tools=[ANSWER_TOOL],
                tool_choice={
                    "type": "function",
                    "function": {"name": "answer_question"},
                },
            )

            # Parse the tool call's structured arguments.
            tool_calls = resp.choices[0].message.tool_calls or []
            if not tool_calls:
                # Defensive — should not happen because tool_choice forces it,
                # but if a provider misbehaves we want a clear error.
                raise RuntimeError("LLM did not call the answer_question tool")
            args_json = tool_calls[0].function.arguments
            args = json.loads(args_json)

            # Compute real cost from usage.
            usage = resp.usage
            cost = compute_cost_usd(
                settings.model,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
            )

            return Answer(
                content=args["content"],
                confidence=args["confidence"],
                sources=args.get("sources", []),
                cost_usd=cost,
                retries=attempt,
                schema_version="v1",
            )

        except Exception as exc:
            last_err = exc
            if attempt < settings.max_retries:
                logger.warning(
                    "ask_llm attempt %d failed: %s — retrying", attempt + 1, exc
                )
                await asyncio.sleep(settings.retry_delay_s * (2 ** attempt))
                continue
            raise

    raise RuntimeError(f"ask_llm exhausted retries: {last_err}")  # unreachable


async def ask_llm_with_retry(
    q,
    tries: int = 3,
    fail_rate: float = 0.0,
):
    """Backward-compatible W2/W3 retry wrapper."""

    for attempt in range(tries):
        try:
            answer = await ask_llm(q)

            if hasattr(answer, "retries"):
                answer.retries = attempt

            return answer

        except Exception:
            if attempt == tries - 1:
                raise

            await asyncio.sleep(2 ** attempt)

    raise RuntimeError("Retry loop exited unexpectedly")

# ─── Streaming endpoint ─────────────────────────────────────────────────────
async def stream_answer(
    question: str, settings: Settings | None = None
) -> AsyncIterator[str]:
    """Yield content tokens as they arrive from the LLM.

    Real OpenAI streaming — no asyncio.sleep, no word-splitting.
    """
    settings = settings or Settings()

    if settings.use_fake:
        full = await fake_ask_llm(question)
        for word in full.split(" "):
            await asyncio.sleep(0.05)
            yield word + " "
        return

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    stream = await client.chat.completions.create(
        model=settings.model,
        messages=[{"role": "user", "content": question}],
        stream=True,
    )

    async for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
