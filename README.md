# Growth.ia

Aplicacao full-stack de IA para e-commerce com foco em backend analitico, agentes e integracao com dados.

## Glacier AI Backend

Backend em Python para um agente analitico de e-commerce usando FastAPI, LangGraph, OpenAI e BigQuery.

As referencias das tabelas essenciais do dataset publico `thelook_ecommerce`
ficam centralizadas em `app/core/bigquery_tables.py` e sao consumidas pela
camada de repository.

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
- `BACKEND_CORS_ORIGINS`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `LOCAL_CACHE_DB_PATH`
- `CACHE_REFRESH_MINUTES`

## Instalacao

```bash
pip install -r requirements.txt
```

## Rodando o backend

```bash
uvicorn app.main:app --reload
```

## Frontend minimo

O frontend de validacao da experiencia fica em `frontend/`.

Variaveis de ambiente opcionais do frontend:

- `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000`
- `NEXT_PUBLIC_USE_MOCK_API=false`

O backend libera CORS por padrao para `http://localhost:3000` e
`http://127.0.0.1:3000`. Se voce rodar o frontend em outra origem, ajuste
`BACKEND_CORS_ORIGINS` com uma lista separada por virgula.

Para rodar localmente:

```bash
cd frontend
npm install
npm run dev
```

Se o backend ainda nao estiver disponivel, voce pode usar mock local:

```bash
cd frontend
copy .env.example .env.local
```

Depois altere:

```bash
NEXT_PUBLIC_USE_MOCK_API=true
```

## Testes

```bash
pytest
```

## Credenciais

O acesso ao BigQuery depende da variavel `GOOGLE_APPLICATION_CREDENTIALS` apontando
para um arquivo de service account com permissao para consultar datasets publicos.

## Cache local SQLite

O projeto agora possui uma Fase 1 de arquitetura hibrida:

- BigQuery continua como fonte de verdade
- SQLite guarda snapshots locais para leitura futura pela UI/dashboard
- nesta fase, o backend principal ainda nao le do cache local por padrao

Configuracoes relevantes:

- `LOCAL_CACHE_DB_PATH=data/glacier_cache.db`
- `CACHE_REFRESH_MINUTES=10`

Para sincronizar snapshots manualmente:

```bash
python scripts/sync_bigquery_cache.py
```

O arquivo SQLite padrao sera criado em `data/glacier_cache.db`.

## Status

- Fase 1 concluida: configuracao centralizada e schemas base.
- Fase 2 concluida: camada de dados com BigQueryService e AnalyticsRepository.
- Fase 3 concluida: tools, LLM service, agente LangGraph e testes unitarios da camada agentic.
- Fase 4 concluida: camada HTTP com FastAPI, endpoint /ask, healthcheck e testes de endpoint.
- Fase 5A.1 + 5B concluida: validacao real manual, logs estruturados, request_id e timing minimo.
- UI minima concluida: interface de chat em Next.js para validar a experiencia antes do dashboard.

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
