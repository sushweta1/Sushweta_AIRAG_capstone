from __future__ import annotations

import json

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.pipeline.settings import Settings


class JudgeVerdict(BaseModel):
    accuracy: int = Field(ge=1, le=4)
    groundedness: int = Field(ge=1, le=4)
    format: int = Field(ge=1, le=4)
    reasoning: str


JUDGE_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "score_candidate",
        "description": (
            "Score a candidate answer against the reference answer "
            "using the supplied evaluation rubric."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "accuracy": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                },
                "groundedness": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                },
                "format": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 4,
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Brief explanation of the scores, including "
                        "specific strengths or problems in the candidate answer."
                    ),
                },
            },
            "required": [
                "accuracy",
                "groundedness",
                "format",
                "reasoning",
            ],
        },
    },
}


JUDGE_RUBRIC = """
You are a senior evaluator assessing the quality of an AI assistant answer.

Evaluate the CANDIDATE ANSWER against the QUESTION and IDEAL ANSWER.
Score each dimension from 1 to 4.

ACCURACY
4 - Completely correct. The important claims agree with the ideal answer
    and there are no substantive factual errors.
3 - Mostly correct. The main answer is correct but there is a minor
    inaccuracy, omission, or imprecision that does not change the conclusion.
2 - Partially correct. Some useful information is present, but there is
    a meaningful error, omission, or conflation that could mislead the user.
1 - Incorrect. The main claim is wrong, contradicts the ideal answer,
    or fails to answer the question.

GROUNDEDNESS
4 - Fully supported by the information represented in the ideal answer.
    It does not introduce unsupported factual claims.
3 - Mostly grounded, but contains a small unsupported extension or
    unnecessary claim that does not materially change the answer.
2 - Partly grounded. It mixes supported information with one or more
    important unsupported claims or assumptions.
1 - Poorly grounded. The answer is largely unsupported, fabricated,
    or ignores the available reference information.

FORMAT
4 - Clear, concise, directly answers the question, and is easy to read.
3 - Understandable and relevant, but has a minor clarity, verbosity,
    structure, or formatting issue.
2 - Noticeably unclear, overly verbose, incomplete, or poorly structured.
1 - Very difficult to understand, badly formatted, or does not provide
    a usable answer.

Important:
- Judge the substance, not confidence of tone.
- Do not reward an answer merely because it sounds authoritative.
- For an out-of-scope question, correctly saying that the available
  knowledge cannot support an answer should receive a high score.
- Use the score anchors above consistently.
- Return the scores using the score_candidate tool.
"""


async def judge_answer(
    question: str,
    candidate_answer: str,
    ideal_answer: str,
    settings: Settings | None = None,
) -> JudgeVerdict:
    """Use an LLM judge to score one candidate answer."""

    settings = settings or Settings()

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            "Set it before running the W5 evaluation."
        )

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = f"""
{JUDGE_RUBRIC}

QUESTION:
{question}

IDEAL ANSWER:
{ideal_answer}

CANDIDATE ANSWER:
{candidate_answer}
"""

    response = await client.chat.completions.create(
        model=settings.model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        tools=[JUDGE_TOOL],
        tool_choice={
            "type": "function",
            "function": {"name": "score_candidate"},
        },
        temperature=0,
    )

    tool_calls = response.choices[0].message.tool_calls or []

    if not tool_calls:
        raise RuntimeError("Judge did not call the score_candidate tool")

    arguments = json.loads(tool_calls[0].function.arguments)

    return JudgeVerdict.model_validate(arguments)