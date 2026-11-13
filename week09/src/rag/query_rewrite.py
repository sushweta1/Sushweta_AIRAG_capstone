"""Query rewriting techniques — Stretch lab for W9.

Three patterns:
  hyde_rewrite(question)        → str (a hypothetical answer to embed)
  multi_query_rewrite(question) → list[str] (3 paraphrases)
  step_back_rewrite(question)   → str (a more general framing)

All three add an LLM call per query — cost ~$0.0001 per rewrite at
gpt-4o-mini rates. Trade-off: better retrieval recall vs cost+latency.

When to use each (curriculum's guidance):
  * HyDE — when queries are short/vague and the corpus has rich,
    detailed passages. The hypothetical answer is more similar to a
    real chunk than the bare question is.
  * Multi-Query — when queries have synonyms or terminology mismatch
    with the corpus. The union of 3 retrievals covers more ground.
  * Step-Back — when queries are very specific and the corpus has
    higher-level material. The more general query finds context the
    narrow one misses.
"""
from __future__ import annotations

# Bootstrap before any heavy import
from src import _bootstrap  # noqa: F401

from openai import OpenAI

# Lazy OpenAI client (same pattern as qdrant_rag)
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


REWRITE_MODEL = "gpt-4o-mini"


# ─── HyDE ───────────────────────────────────────────────────────────────

HYDE_PROMPT = (
    "You are answering an internal knowledge-base question. Draft a "
    "short, plausible answer (2-3 sentences). The answer doesn't need "
    "to be correct — it just needs to use the kind of language and "
    "detail a real policy document would use. Do not preface with 'Here "
    "is an answer:' or similar. Output only the answer text."
)


def hyde_rewrite(question: str, model: str = REWRITE_MODEL) -> str:
    """HyDE — draft a hypothetical answer to embed in place of the question.

    The hypothetical answer is embedding-similar to real chunks in the
    corpus (which contain real answers). The question alone often isn't —
    questions and answers don't share much vocabulary.

    Args:
        question: the original user question.
        model: OpenAI chat model.

    Returns:
        A hypothetical answer string to use as the retrieval query.
    """
    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": HYDE_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


# ─── Multi-Query ────────────────────────────────────────────────────────

MULTIQUERY_PROMPT = (
    "Given a user's question, generate exactly 3 alternative phrasings "
    "that capture the same intent but use different vocabulary. "
    "Output only the 3 questions, one per line. No numbering, no "
    "preamble. Each phrasing should be a complete question."
)


def multi_query_rewrite(question: str, n: int = 3,
                         model: str = REWRITE_MODEL) -> list[str]:
    """Multi-Query — generate N paraphrases for vocabulary coverage.

    The retriever runs against each paraphrase; results are unioned and
    deduplicated. Helps when the original query uses different vocabulary
    than the corpus.

    Args:
        question: the original user question.
        n: how many paraphrases to generate (default 3).
        model: OpenAI chat model.

    Returns:
        List of N paraphrase strings (does NOT include the original).
    """
    prompt = MULTIQUERY_PROMPT
    if n != 3:
        prompt = prompt.replace("exactly 3", f"exactly {n}").replace("the 3", f"the {n}")
    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.5,
        max_tokens=300,
    )
    text = response.choices[0].message.content.strip()
    # Split by newline, drop empty lines, trim each
    lines = [line.strip(" \t-•*0123456789.").strip() for line in text.splitlines()]
    lines = [l for l in lines if l and len(l) > 5]
    return lines[:n]


# ─── Step-Back ──────────────────────────────────────────────────────────

STEPBACK_PROMPT = (
    "Given a user's specific question, generate a more general 'step-back' "
    "question that captures the broader topic. The step-back question "
    "should help find higher-level context that the specific question "
    "might miss. Output only the step-back question. No preamble."
)


def step_back_rewrite(question: str, model: str = REWRITE_MODEL) -> str:
    """Step-Back — generate a more general version of the question.

    The original Google paper: 'Take a Step Back: Evoking Reasoning via
    Abstraction in Large Language Models' (Zheng et al. 2023). Idea: a
    more general question finds context the specific one misses; then
    use BOTH context blocks when generating the final answer.

    Args:
        question: the original (specific) user question.
        model: OpenAI chat model.

    Returns:
        A more general step-back question string.
    """
    response = _get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": STEPBACK_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.3,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


# ─── Convenience: retrieve with rewrite applied ─────────────────────────

def retrieve_with_rewrite(
    technique: str,
    question: str,
    retrieve_fn,
    **retrieve_kwargs,
) -> list[dict]:
    """Apply a rewrite technique, then call the given retrieve function.

    Args:
        technique: one of 'hyde', 'multi_query', 'step_back'.
        question: the original question.
        retrieve_fn: callable that takes (query, **kwargs) → list[dict].
        retrieve_kwargs: passed through to retrieve_fn.

    Returns:
        Combined results from the rewritten query / queries.

    For multi_query, results from all paraphrases are unioned and
    deduplicated by (source, text[:100]) before being returned in
    score order.
    """
    if technique == "hyde":
        new_query = hyde_rewrite(question)
        return retrieve_fn(query=new_query, **retrieve_kwargs)

    if technique == "step_back":
        # Run BOTH the original and the step-back query; union+dedup
        stepback = step_back_rewrite(question)
        results_orig = retrieve_fn(query=question, **retrieve_kwargs)
        results_back = retrieve_fn(query=stepback, **retrieve_kwargs)
        seen = set()
        merged = []
        for r in results_orig + results_back:
            key = (r.get("source", ""), r.get("text", "")[:100])
            if key in seen:
                continue
            seen.add(key)
            merged.append(r)
        return merged

    if technique == "multi_query":
        paraphrases = multi_query_rewrite(question)
        # Include the original too — paraphrases supplement, don't replace
        all_queries = [question] + paraphrases
        seen = set()
        merged = []
        for q in all_queries:
            for r in retrieve_fn(query=q, **retrieve_kwargs):
                key = (r.get("source", ""), r.get("text", "")[:100])
                if key in seen:
                    continue
                seen.add(key)
                merged.append(r)
        return merged

    raise ValueError(
        f"Unknown technique {technique!r}. "
        f"Choose: 'hyde', 'multi_query', or 'step_back'."
    )
