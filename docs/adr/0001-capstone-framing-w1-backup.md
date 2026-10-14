# ADR-0001: Capstone Framing — FastAPI Knowledge Assistant

- **Status:** Draft v1
- **Date:** 2026-09-06
- **Author:** Sushweta Biswas

## Context

Developers learning or using FastAPI often need to find answers across multiple documentation pages covering request validation, dependencies, async programming, testing, and deployment.

This capstone will build a Q&A assistant over a small corpus of official FastAPI documentation so that users can ask natural-language questions and receive concise, grounded answers.

## Decision — Solution Framing Canvas

| Box | Your answer |
|-----|-------------|
| **Inputs** | A natural-language question about the selected FastAPI documentation. |
| **Outputs** | A concise answer to the user's question, grounded in the relevant FastAPI documentation. |
| **Tools** | An OpenAI model for answer generation and, in later weeks, a retrieval system over the FastAPI documentation corpus. |
| **Memory** | No durable memory across sessions in v1; each question is handled independently. |
| **Autonomy level** | Q&A assistant: it answers questions using the available documentation but does not take external actions. |
| **Decision boundaries** | It may answer questions supported by the selected FastAPI documentation. If the available evidence is insufficient or ambiguous, it should say that it is unsure rather than invent an answer. |

## Consequences

- **Positive:**
  - Provides faster access to relevant FastAPI guidance.
  - Grounded answers will make information easier to verify.
  - A small public documentation corpus keeps the initial scope manageable.

- **Negative / risks:**
  - FastAPI documentation may change over time.
  - Retrieval may fail to find the most relevant documentation.
  - Model-generated answers may still be inaccurate if grounding is weak.

- **Things we'll re-visit:**
  - Retrieval and chunking strategy in later weeks.
  - Whether multi-turn memory is needed.
  - How citations and confidence should be presented to users.