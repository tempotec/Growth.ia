# Glacier AI Backend

Backend em Python para um agente analítico de e-commerce com FastAPI, LangGraph, OpenAI e BigQuery.

## Stack

- Python 3.10+
- FastAPI
- LangGraph
- Pydantic
- OpenAI
- Google BigQuery

## Variáveis de ambiente

Use o arquivo `.env.example` como referência:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GOOGLE_APPLICATION_CREDENTIALS`

## Instalação

```bash
pip install -r requirements.txt
```

## Credenciais

O acesso ao BigQuery depende da variável `GOOGLE_APPLICATION_CREDENTIALS` apontando
para um arquivo de service account com permissão para consultar datasets públicos.

Nesta fase, o projeto contém a base de configuração, os schemas iniciais e a camada
de dados usada nas próximas etapas.
