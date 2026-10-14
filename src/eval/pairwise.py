from __future__ import annotations

import json
import random

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.pipeline.settings import Settings


class PairwiseVerdict(BaseModel):
    winner: str
    reasoning: str


PAIRWISE_TOOL = {
    "type": "function",
    "function": {
        "name": "choose_better_answer",
        "description": "Choose which answer better satisfies the question.",
        "parameters": {
            "type": "object",
            "properties": {
                "winner": {
                    "type": "string",
                    "enum": ["A", "B", "tie"],
                },
                "reasoning": {
                    "type": "string",
                },
            },
            "required": ["winner", "reasoning"],
        },
    },
}

async def pairwise_compare(
    question: str,
    ideal_answer: str,
    answer_a: str,
    answer_b: str,
    settings: Settings | None = None,
) -> PairwiseVerdict:


    settings = settings or Settings()

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = f"""
You are comparing two candidate answers against the expected answer.

The order of Answer A and Answer B is arbitrary. Do not prefer an answer
because it appears first or second.

Choose A or B only when one answer is materially better against the expected
answer. Do not choose a winner for minor wording differences, extra detail,
or stylistic differences. If both answers are substantially equivalent,
choose tie.

Treat two answers as a tie when both correctly capture the core meaning of
the expected answer, even if one includes an extra detail or omits a minor
detail.

Do not declare a winner solely because one answer is more complete, longer,
or closer in wording to the expected answer. A winner should be chosen only
when the difference materially affects correctness, grounding, relevance, or
appropriate refusal behavior.

Choose the candidate that better matches the expected answer in:
- accuracy
- groundedness
- relevance
- appropriate handling of out-of-scope questions
- clarity

Do not reward an answer merely because it is detailed or generally useful.
If the expected answer says the question is outside the available FastAPI
documentation, prefer a candidate that correctly refuses rather than one
that answers from general knowledge.

QUESTION:
{question}

EXPECTED ANSWER:
{ideal_answer}

ANSWER A:
{answer_a}

ANSWER B:
{answer_b}
"""

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        tools=[PAIRWISE_TOOL],
        tool_choice={
            "type": "function",
            "function": {"name": "choose_better_answer"},
        },
        temperature=0,
    )

    tool_calls = response.choices[0].message.tool_calls or []
    if not tool_calls:
        raise RuntimeError("Pairwise judge did not return a tool call")

    arguments = json.loads(tool_calls[0].function.arguments)
    return PairwiseVerdict.model_validate(arguments)

async def pairwise_compare_with_flip(
    question: str,
    ideal_answer: str,
    answer_v1: str,
    answer_v2: str,
    settings: Settings | None = None,
) -> dict:
    forward = await pairwise_compare(
    question,
    ideal_answer,
    answer_v1,
    answer_v2,
    settings,
    )

    reverse = await pairwise_compare(
        question,
        ideal_answer,
        answer_v2,
        answer_v1,
        settings,
    )

    if forward.winner == "A" and reverse.winner == "B":
        overall = "v1"
    elif forward.winner == "B" and reverse.winner == "A":
        overall = "v2"
    elif forward.winner == "tie" and reverse.winner == "tie":
        overall = "tie"
    else:
        overall = "ambiguous"

    return {
        "forward": forward.model_dump(),
        "reverse": reverse.model_dump(),
        "overall_winner": overall,
    }