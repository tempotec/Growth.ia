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

## Rodando o backend

```bash
uvicorn app.main:app --reload
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
- Fase 5A.1 + 5B concluida: validacao real manual, logs estruturados, request_id e timing minimo.

Neste momento, o repositorio contem a base do backend Glacier AI, incluindo
configuracao centralizada, schemas, camada de dados, fluxo agentic, camada HTTP
e testes unitarios para os blocos implementados.

## Validacao real manual

Variaveis de ambiente necessarias:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS`

### Validar BigQuery real

```bash
python scripts/validate_real_services.py --service bigquery
```

### Validar OpenAI real

```bash
python scripts/validate_real_services.py --service openai
```

### Validar ambos

```bash
python scripts/validate_real_services.py --service all
```

## Smoke tests manuais do /ask

Com o backend rodando localmente:

```bash
curl -X POST http://127.0.0.1:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Como foi o volume de usuarios vindos de Search no ultimo mes?\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Qual canal teve mais receita?\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"question\":\"Qual canal teve melhor performance e por que?\"}"
```

## Logs basicos

Os logs locais agora registram, no minimo:

- `request_id` por request
- inicio e fim da request HTTP
- intent detectada
- tool selecionada
- tempo total da request
- tempo da query no BigQuery
- tempo das chamadas da LLM
- erro controlado vs erro inesperado
