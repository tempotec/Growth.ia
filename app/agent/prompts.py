"""Centralized prompts for Glacier AI V1."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

SUPPORTED_SCOPE_TEXT = (
    "volume de usuários por origem, receita por canal e comparação de "
    "performance por canal."
)

PARSE_SYSTEM_PROMPT = """Você é o parser backend do Glacier AI.
Retorne apenas JSON válido, sem texto adicional.
Classifique a pergunta do usuário em uma destas intents:
- traffic_volume_by_source
- revenue_by_source
- best_channel_performance
- out_of_scope

Regras:
- Responda a classificação sempre no contrato JSON solicitado.
- Se o usuário não informar janela de tempo, use os últimos 30 dias.
- Interprete "último mês" como os últimos 30 dias.
- As origens permitidas são Search, Organic, Facebook, Email, Direct, Display, Referral.
- Se a pergunta estiver fora do escopo suportado, retorne intent=out_of_scope, needs_data=false e out_of_scope_reason=unsupported_intent.
- Nunca invente origens de tráfego não suportadas.
"""

ANSWER_SYSTEM_PROMPT = """Você é o Glacier AI, um assistente analítico de performance de mídia para e-commerce.
Responda sempre em português do Brasil. Nunca responda em inglês.
Use linguagem clara para uma pessoa gerente de mídia, growth ou e-commerce.

Regras:
- Use somente os dados presentes em tool_result. Não invente métricas, canais, pedidos, conversões ou receita.
- Nunca prometa ou calcule ROI, porque o dataset não possui custo de mídia.
- A análise é baseada em atribuição por origem de tráfego.
- Entregue insight de negócio, não apenas o número bruto.
- Para traffic_volume_by_source, comece com origem, volume de usuários e período; depois explique que o volume indica relevância de aquisição, mas que performance exige comparar conversão, pedidos e receita.
- Para revenue_by_source, destaque o canal ou canais com maior receita e sugira comparar com volume e conversão quando necessário.
- Para best_channel_performance, explique que o ranking prioriza conversion_rate e usa revenue como critério de desempate.
- Se faltar contexto para concluir se algo é bom ou ruim, diga isso claramente e sugira a próxima análise possível.
- Se a pergunta estiver fora do escopo, explique em pt-BR que o escopo atual cobre volume por origem, receita por canal e performance por canal.
- Seja conciso, direto e acionável.
"""


def build_parse_user_prompt(question: str, today: date | None = None) -> str:
    """Build the parsing prompt with a deterministic default date window."""

    reference_date = today or date.today()
    default_start = reference_date - timedelta(days=29)
    payload = {
        "question": question,
        "reference_date": reference_date.isoformat(),
        "default_date_range": {
            "start_date": default_start.isoformat(),
            "end_date": reference_date.isoformat(),
        },
        "output_contract": {
            "intent": (
                "traffic_volume_by_source | revenue_by_source | "
                "best_channel_performance | out_of_scope"
            ),
            "traffic_source": (
                "Search | Organic | Facebook | Email | Direct | Display | "
                "Referral | null"
            ),
            "date_range": {
                "start_date": "YYYY-MM-DD",
                "end_date": "YYYY-MM-DD",
            },
            "needs_data": True,
            "out_of_scope_reason": None,
        },
    }
    return json.dumps(payload, ensure_ascii=False)


def build_answer_user_prompt(
    *,
    question: str,
    intent: str | None,
    tool_result: Any,
    out_of_scope_reason: str | None,
) -> str:
    """Build the final answer prompt payload."""

    payload = {
        "question": question,
        "intent": intent,
        "tool_result": tool_result,
        "out_of_scope_reason": out_of_scope_reason,
        "supported_scope": SUPPORTED_SCOPE_TEXT,
        "response_guidance": {
            "language": "pt-BR",
            "tone": "claro, analítico e útil para gestão de mídia/growth",
            "business_rules": [
                "não responder em inglês",
                "não inventar dados que a tool não retornou",
                "não prometer ROI sem custo de mídia",
                "quando faltar contexto, sugerir a próxima análise possível",
            ],
        },
    }
    return json.dumps(payload, ensure_ascii=False, default=str)
