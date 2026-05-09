"""Unit tests for answer style detection."""

from __future__ import annotations

from app.agent.answer_style import detect_answer_style, limit_sentences


def test_detect_answer_style_marks_short_answer_requests() -> None:
    questions = [
        "Me dê uma conclusão curta e prática.",
        "Me dê uma recomendação final em uma frase.",
        "Resuma em uma frase.",
        "Seja direto e objetivo.",
    ]

    for question in questions:
        style = detect_answer_style(question)

        assert style["short_answer"] is True
        assert style["max_sentences"] == 2
        assert style["use_default_answer_structure"] is False


def test_detect_answer_style_keeps_default_mode_for_regular_questions() -> None:
    style = detect_answer_style("Qual canal teve melhor performance?")

    assert style["short_answer"] is False
    assert style["max_sentences"] is None
    assert style["use_default_answer_structure"] is True


def test_limit_sentences_keeps_only_requested_number_of_sentences() -> None:
    answer = "Primeira frase. Segunda frase. Terceira frase."

    assert limit_sentences(answer, 2) == "Primeira frase. Segunda frase."
