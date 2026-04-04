from __future__ import annotations

import json

from openai import OpenAI

from app.core.config import get_settings


def build_judge_prompt(question: str, retrieved_evidence: str, generated_answer: str) -> str:
    return f"""
You are grading an enterprise analytics assistant.

Question:
{question}

Retrieved evidence:
{retrieved_evidence}

Generated answer:
{generated_answer}

Return JSON with numeric scores from 0 to 1 for:
- faithfulness
- completeness
- citation_accuracy

Also return a short explanation string for each score.
Only judge based on the supplied evidence.
""".strip()


def judge_answer(question: str, retrieved_evidence: str, generated_answer: str) -> dict:
    settings = get_settings()
    if not settings.openai_api_key:
        return {
            "faithfulness": None,
            "completeness": None,
            "citation_accuracy": None,
            "notes": "LLM judge skipped because OPENAI_API_KEY is not configured.",
        }

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_chat_model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are an evaluation judge for grounded AI answers."},
            {
                "role": "user",
                "content": build_judge_prompt(question, retrieved_evidence, generated_answer),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
