from __future__ import annotations

from pydantic import BaseModel, Field


class CriticVerdict(BaseModel):
    accuracy: int = Field(ge=1, le=4)
    groundedness: int = Field(ge=1, le=4)
    format: int = Field(ge=1, le=4)
    feedback: str


def mean_score(verdict: CriticVerdict) -> float:
    return (
        verdict.accuracy
        + verdict.groundedness
        + verdict.format
    ) / 3


import json

from openai import AsyncOpenAI

from src.pipeline.settings import Settings


CRITIC_TOOL = {
    "type": "function",
    "function": {
        "name": "critique_answer",
        "description": "Score the candidate answer and provide improvement feedback.",
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
                "feedback": {
                    "type": "string",
                },
            },
            "required": [
                "accuracy",
                "groundedness",
                "format",
                "feedback",
            ],
        },
    },
}


async def critique_answer(
    question: str,
    ideal_answer: str,
    candidate_answer: str,
    settings: Settings | None = None,
) -> CriticVerdict:
    settings = settings or Settings()

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = f"""
Evaluate the candidate answer against the expected answer.

Score each dimension from 1 to 4:
- accuracy
- groundedness
- format

Then provide specific feedback explaining what should be improved.

QUESTION:
{question}

EXPECTED ANSWER:
{ideal_answer}

CANDIDATE ANSWER:
{candidate_answer}
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        tools=[CRITIC_TOOL],
        tool_choice={
            "type": "function",
            "function": {"name": "critique_answer"},
        },
        temperature=0,
    )

    tool_calls = response.choices[0].message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("Critic did not return a tool call")

    arguments = json.loads(tool_calls[0].function.arguments)
    return CriticVerdict.model_validate(arguments)

async def revise_answer(
    question: str,
    ideal_answer: str,
    current_answer: str,
    feedback: str,
    settings: Settings | None = None,
) -> str:
    settings = settings or Settings()

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = f"""
Improve the candidate answer using the critic feedback.

Keep the answer concise and directly relevant.
Do not add unsupported information.
If the question is outside the available FastAPI documentation, explicitly say
that the available FastAPI documentation is insufficient rather than answering
from general knowledge.

QUESTION:
{question}

EXPECTED ANSWER:
{ideal_answer}

CURRENT ANSWER:
{current_answer}

CRITIC FEEDBACK:
{feedback}
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content.strip()