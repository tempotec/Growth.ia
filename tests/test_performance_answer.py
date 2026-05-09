"""Unit tests for deterministic multi-criteria performance answers."""

from __future__ import annotations

from app.agent.performance_answer import build_best_performance_answer


def _performance_rows() -> list[dict]:
    return [
        {
            "traffic_source": "Facebook",
            "users": 214,
            "converted_users": 182,
            "orders": 297,
            "revenue": 42300.0,
            "conversion_rate": 0.8504,
        },
        {
            "traffic_source": "Search",
            "users": 2493,
            "converted_users": 1984,
            "orders": 3094,
            "revenue": 622593.8,
            "conversion_rate": 0.7958,
        },
        {
            "traffic_source": "Display",
            "users": 141,
            "converted_users": 115,
            "orders": 160,
            "revenue": 36000.0,
            "conversion_rate": 0.816,
        },
    ]


def test_build_best_performance_answer_explains_multiple_criteria() -> None:
    answer = build_best_performance_answer(_performance_rows())

    assert answer is not None
    assert answer.startswith("Depende do critério")
    assert "Facebook lidera em conversão" in answer
    assert "Search lidera em volume" in answer
    assert "Search lidera em receita" in answer
    assert "impacto comercial total, Search" in answer
    assert "eficiência proporcional, Facebook" in answer
    assert "vencedor absoluto" in answer


def test_build_best_performance_answer_respects_filtered_channel_rows() -> None:
    filtered_rows = [
        row
        for row in _performance_rows()
        if row["traffic_source"] in {"Search", "Display"}
    ]

    answer = build_best_performance_answer(filtered_rows)

    assert answer is not None
    assert "Display lidera em conversão" in answer
    assert "Search lidera em volume" in answer
    assert "Search lidera em receita" in answer
    assert "Facebook" not in answer


def test_build_best_performance_answer_short_mode_returns_two_sentences() -> None:
    answer = build_best_performance_answer(_performance_rows(), short_answer=True)

    assert answer is not None
    assert answer.count(".") == 2
    assert "Facebook lidera em conversão" in answer
    assert "Search lidera em volume" in answer
    assert "Search lidera em receita" in answer
