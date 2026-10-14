"""tests/test_pipeline.py — Week 3 Lab Step 2.

Two mocked unit tests. We mock the boundary layer (fake_ask_llm)
and verify behaviour of the wrappers above it.

The production W2 setting uses use_fake=False, so these tests
temporarily patch it to True.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.pipeline.fake_llm import Question, Answer, FakeLLMError
import src.pipeline.pipeline as pipeline
from src.pipeline.pipeline import ask_llm, ask_llm_with_retry


@pytest.mark.asyncio
async def test_ask_llm_calls_fake_once():
    q = Question(text="What is RAG?")

    with patch.object(pipeline._settings_for_import, "use_fake", True):
        with patch(
            "src.pipeline.pipeline.fake_ask_llm",
            new_callable=AsyncMock,
        ) as mock_fake:
            mock_fake.return_value = Answer(
                question=q.text,
                text="Fake answer",
                cost_usd=0.0,
                retries=0,
            )

            result = await ask_llm(q)

            mock_fake.assert_awaited_once()
            assert result.text == "Fake answer"


@pytest.mark.asyncio
async def test_retry_three_times_on_failure():
    q = Question(text="What is RAG?")

    with patch.object(pipeline._settings_for_import, "use_fake", True):
        with patch(
            "src.pipeline.pipeline.fake_ask_llm",
            AsyncMock(side_effect=FakeLLMError("simulated")),
        ) as m_call, patch(
            "src.pipeline.pipeline.asyncio.sleep",
            AsyncMock(),
        ):
            with pytest.raises(FakeLLMError):
                await ask_llm_with_retry(q, tries=3)

        assert m_call.call_count == 3