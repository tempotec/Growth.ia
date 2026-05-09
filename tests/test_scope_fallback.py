"""Unit tests for useful unsupported-scope fallbacks."""

from __future__ import annotations

from app.agent.scope_fallback import DATASET_GAP_REASON, resolve_scope_fallback


def _campaign_history() -> list[dict]:
    return [
        {
            "role": "assistant",
            "content": (
                "Não tenho dados de campanha ou criativo no dataset atual. "
                "A análise mais próxima é comparar canais de tráfego."
            ),
        }
    ]


def test_scope_fallback_handles_campaign_creative_questions() -> None:
    result = resolve_scope_fallback(
        "Qual campanha teve o melhor criativo?",
        conversation_history=[],
    )

    assert result is not None
    assert result["intent"] == "out_of_scope"
    assert result["out_of_scope_reason"] == DATASET_GAP_REASON
    assert result["tool_name"] is None
    assert "Não tenho dados de campanha ou criativo" in result["answer"]
    assert "impressões" in result["answer"]
    assert "canais de tráfego" in result["answer"]
    assert "CPA" not in result["answer"]
    assert "CAC" not in result["answer"]
    assert "ROAS" not in result["answer"]


def test_scope_fallback_answers_available_data_followup_from_history() -> None:
    result = resolve_scope_fallback(
        "Você consegue responder isso com os dados disponíveis?",
        conversation_history=_campaign_history(),
    )

    assert result is not None
    assert "Não consigo responder diretamente sobre campanha ou criativo" in result["answer"]
    assert "comparar canais de tráfego" in result["answer"]


def test_scope_fallback_explains_missing_data_from_history() -> None:
    result = resolve_scope_fallback(
        "Quais dados faltariam?",
        conversation_history=_campaign_history(),
    )

    assert result is not None
    assert "Faltariam dados por campanha ou criativo" in result["answer"]
    assert "impressões" in result["answer"]
    assert "pedidos e receita" in result["answer"]


def test_scope_fallback_answers_current_dataset_alternative_directly() -> None:
    result = resolve_scope_fallback(
        "Com o dataset atual, qual análise parecida você consegue fazer?",
        conversation_history=_campaign_history(),
    )

    assert result is not None
    assert "Com o dataset atual" in result["answer"]
    assert "usuários convertidos" in result["answer"]
    assert "não identifica o melhor criativo" in result["answer"]


def test_scope_fallback_answers_channel_alternative_request() -> None:
    result = resolve_scope_fallback(
        "Então me dê uma alternativa útil usando os canais de tráfego.",
        conversation_history=_campaign_history(),
    )

    assert result is not None
    assert "comparar canais de tráfego" in result["answer"]
    assert "pedidos e receita" in result["answer"]
