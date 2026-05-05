# Growth.ia

Aplicacao full-stack de IA para e-commerce com foco em backend analitico, agentes e integracao com dados.

## Glacier AI Backend

Backend em Python para um agente analitico de e-commerce usando FastAPI, LangGraph, OpenAI e BigQuery.

## Stack

- Python 3.10+
- FastAPI
- LangGraph
- Pydantic
- OpenAI
- Google BigQuery

## Variaveis de ambiente

Use o arquivo `.env.example` como referencia:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS`

## Instalacao

```bash
pip install -r requirements.txt
```

## Testes

```bash
pytest
```

## Credenciais

O acesso ao BigQuery depende da variavel `GOOGLE_APPLICATION_CREDENTIALS` apontando
para um arquivo de service account com permissao para consultar datasets publicos.

## Status

- Fase 1 concluida: configuracao centralizada e schemas base.
- Fase 2 concluida: camada de dados com BigQueryService e AnalyticsRepository.
- Fase 3 concluida: tools, LLM service, agente LangGraph e testes unitarios da camada agentic.
- Fase 4 concluida: camada HTTP com FastAPI, endpoint /ask, healthcheck e testes de endpoint.

Neste momento, o repositorio contem a base do backend Glacier AI, incluindo
configuracao centralizada, schemas, camada de dados, fluxo agentic, camada HTTP
e testes unitarios para os blocos implementados.
