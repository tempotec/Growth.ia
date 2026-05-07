# 🚀 Glacier AI - Agente Autônomo de Analytics

Agente de inteligência artificial autônomo que responde perguntas sobre performance de e-commerce em linguagem natural.

## 📋 O que faz

**Você faz uma pergunta** → **Agente identifica intenção** → **Chama tool Python** → **Consulta BigQuery** → **Gera resposta natural**

Exemplos de perguntas que o agente responde:
- "Como foi o volume de usuários vindos de Search no último mês?"
- "Qual dos canais tem a melhor performance? E por que?"
- "Qual canal gerou mais receita?"

## 🏗️ Arquitetura

```
Usuário
   ↓
POST /ask (JSON com pergunta em linguagem natural)
   ↓
FastAPI Router
   ↓
LangGraph Agent (entender intenção)
   ├─ Parse da pergunta
   ├─ Roteamento para ferramenta
   ├─ Execução da ferramenta (BigQuery/SQLite)
   └─ Geração de resposta natural
   ↓
AskResponse (resposta + dados + ferramenta usada)
```

## 🛠️ Stack

- **Backend**: Python 3.10+ | FastAPI | LangGraph
- **LLM**: OpenAI GPT-4 Mini
- **Data**: Google BigQuery | SQLite local
- **Frontend**: Next.js 15 | TypeScript | Tailwind CSS
- **Dados**: BigQuery dataset público `thelook_ecommerce`

## 🚀 Setup Rápido

### 1️⃣ Clonar e instalar dependências

```bash
git clone <repo>
cd Growth
pip install -r requirements.txt
```

### 2️⃣ Configurar variáveis de ambiente

Copie o arquivo `.env.example` para `.env`:

```bash
cp .env.example .env
```

### 3️⃣ Configurar OpenAI

Obtenha sua chave em https://platform.openai.com/api-keys

```bash
# .env
OPENAI_API_KEY=sk-proj-xxx...
OPENAI_MODEL=gpt-4-1106-preview
```

### 4️⃣ Configurar Google Cloud / BigQuery

#### Criar Service Account

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Ative a API do BigQuery: **APIs & Services** → **Enable APIs and Services** → Procure por "BigQuery API" → **Enable**
4. Crie uma Service Account: **APIs & Services** → **Credentials** → **Create Credentials** → **Service Account**
5. Após criar, abra a conta → **Keys** → **Add Key** → **Create new key** → **JSON**
6. Salve o arquivo JSON em um local seguro (ex: `secrets/bigquery-key.json`)

#### Configurar variável de ambiente

```bash
# .env
GOOGLE_APPLICATION_CREDENTIALS=/caminho/completo/para/secrets/bigquery-key.json
```

**⚠️ Não commite o arquivo JSON no repositório!** Adicione `secrets/` ao `.gitignore`.

### 5️⃣ Sincronizar cache local

Antes de rodar o backend, sincronize os dados do BigQuery para o cache local:

```bash
python scripts/sync_bigquery_cache.py
```

Isso vai preencher `data/glacier_cache.db` com dados analíticos para evitar latência de query no BigQuery.

### 6️⃣ Rodar Backend

```bash
# Terminal 1 - Backend em porta 8000
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 7️⃣ Rodar Frontend (opcional)

```bash
# Terminal 2 - Frontend em porta 3000
cd frontend
npm install
npm run dev
```

Acesse: **http://localhost:3000**

## 🤖 Testando o Agente /ask

### Validar status da API

```bash
# Health check
curl http://127.0.0.1:8000/health
# Resposta: {"status":"ok"}

# Status do cache
curl http://127.0.0.1:8000/cache/status
```

### Exemplo 1: Volume de usuários por canal

```bash
python -c "import requests; resp = requests.post('http://127.0.0.1:8000/ask', json={'question': 'Como foi o volume de usuários vindos de Search no último mês?'}); print(resp.json())"
```

**Resposta Real:**
```json
{
  "answer": "No último mês, o volume de usuários vindos da origem Search foi de 2.460.",
  "used_tool": "get_users_by_source",
  "data": {
    "traffic_source": "Search",
    "users": 2460,
    "start_date": "2026-04-07",
    "end_date": "2026-05-06"
  },
  "error": null
}
```

### Exemplo 2: Melhor canal por performance

```bash
python -c "import requests; resp = requests.post('http://127.0.0.1:8000/ask', json={'question': 'Qual dos canais tem a melhor performance? E por que?'}); print(resp.json())"
```

**Resposta Real:**
```json
{
  "answer": "O canal com a melhor performance é o Display, pois apresenta a maior taxa de conversão (3,54%). A análise de melhor performance prioriza a taxa de conversão e, em caso de empate, utiliza a receita como critério de desempate. Apesar do Search gerar mais receita total, sua taxa de conversão é menor que a do Display.",
  "used_tool": "get_channel_performance_summary",
  "data": [
    {"traffic_source": "Display", "users": 97, "orders": 343, "revenue": 29604.46, "conversion_rate": 3.54, "start_date": "2026-04-07", "end_date": "2026-05-06"},
    {"traffic_source": "Search", "users": 2460, "orders": 7235, "revenue": 626056.22, "conversion_rate": 2.94, "start_date": "2026-04-07", "end_date": "2026-05-06"}
  ],
  "error": null
}
```

### Exemplo 3: Receita por canal

```bash
python -c "import requests; resp = requests.post('http://127.0.0.1:8000/ask', json={'question': 'Qual canal gerou mais receita?'}); print(resp.json())"
```

**Resposta Real:**
```json
{
  "answer": "O canal que gerou mais receita foi o Search, com R$626.056,22. A análise de melhor canal considera principalmente a taxa de conversão, usando a receita como critério de desempate. Nesse caso, apesar do Display ter a maior taxa de conversão (3,54%), o Search lidera em receita total.",
  "used_tool": "get_channel_performance_summary",
  "data": [
    {"traffic_source": "Display", "users": 97, "orders": 343, "revenue": 29604.46, "conversion_rate": 3.54},
    {"traffic_source": "Search", "users": 2460, "orders": 7235, "revenue": 626056.22, "conversion_rate": 2.94}
  ],
  "error": null
}
```

## 🔧 Tools Implementadas

O agente tem acesso a 3 ferramentas Python para consultar dados:

| Tool | Descrição | Entrada |
|------|-----------|---------|
| `get_users_by_source` | Retorna volume de usuários por canal | `traffic_source`, `start_date`, `end_date` |
| `get_revenue_by_source` | Retorna receita por canal | `traffic_source`, `start_date`, `end_date` |
| `get_channel_performance_summary` | Retorna performance completa (usuários, pedidos, receita, taxa de conversão) | `start_date`, `end_date` |

Cada ferramenta consulta o BigQuery (ou SQLite local) e retorna dados estruturados para o agente processar.

## 📦 Cache Local (SQLite)

O projeto utiliza um sistema híbrido de leitura de dados:

- **Fonte de Verdade**: BigQuery (dados públicos `thelook_ecommerce`)
- **Cache Local**: SQLite (`data/glacier_cache.db`)
- **Uso**: Dashboard lê do cache, agente pode ler de ambos

### Modo de Leitura

| Modo | Uso | Latência |
|------|-----|----------|
| `bigquery_direct` | Agente consulta dados em tempo real | ~2-3s por query |
| `local_cache` | Dashboard lê snapshots sincronizados | <100ms |

Configure em `.env`:
```bash
DATA_SOURCE_MODE=bigquery_direct  # Padrão para o agente
```

### Sincronizar manualmente

```bash
python scripts/sync_bigquery_cache.py
```

Isso popula o SQLite com:
- Performance por canal (usuários, pedidos, receita, conversão)
- Receita por origem
- Usuários por origem

## ⚠️ Limitação Importante: ROI Real Não Incluído

O agente **não calcula ROI real** porque o dataset público não contém:
- ❌ Custo de mídia por canal
- ❌ Custo de aquisição (CAC)
- ❌ Dados de investimento em marketing

**O que o agente faz:**
- ✅ Mede taxa de conversão (usuários → pedidos)
- ✅ Agrupa receita por canal
- ✅ Compara performance relativa

Se seu e-commerce tiver dados de custo de mídia, você pode estender as tools para calcular ROI real adicionando uma tabela com esses dados.

## 🧪 Testes Unitários

```bash
pytest
```

## 📚 Variáveis de Ambiente Completas

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `OPENAI_API_KEY` | Chave da OpenAI | Obrigatória |
| `OPENAI_MODEL` | Modelo GPT | `gpt-4-1106-preview` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path para JSON do GCP | Obrigatória |
| `BACKEND_CORS_ORIGINS` | CORS origins | `http://localhost:3000` |
| `LOCAL_CACHE_DB_PATH` | Path do SQLite | `data/glacier_cache.db` |
| `CACHE_REFRESH_MINUTES` | Intervalo de sync | `10` |
| `DATA_SOURCE_MODE` | Modo de leitura | `bigquery_direct` |


## 🧠 Como o Agente LangGraph Funciona

Quando você faz uma pergunta no `/ask`, aqui está o fluxo completo:

```
1. Parse da Pergunta
   ├─ LLM analisa a pergunta em linguagem natural
   ├─ Extrai intenção (volume? performance? receita?)
   └─ Identifica canais mencionados (se houver)

2. Roteamento para Tool
   ├─ Se pergunta = volume de usuários → get_users_by_source
   ├─ Se pergunta = receita → get_revenue_by_source
   └─ Se pergunta = performance completa → get_channel_performance_summary

3. Execução da Tool
   ├─ Tool consulta BigQuery com parâmetros extraídos
   ├─ Dados são retornados estruturados
   └─ LLM processa os dados

4. Geração de Resposta Natural
   ├─ LLM formata números em moeda/percentuais
   ├─ Ordena dados por relevância
   ├─ Adiciona contexto (por que esse canal é melhor?)
   └─ Retorna resposta em português

5. Resposta JSON
   ├─ answer: texto em linguagem natural
   ├─ used_tool: ferramenta que foi chamada
   ├─ data: dados estruturados brutos
   └─ error: null se sucesso, mensagem se falha
```

## 📁 Estrutura do Projeto

```
Growth/
├── app/
│   ├── agent/               # ← Lógica do agente LangGraph
│   │   ├── graph.py        # Define o grafo de decisão
│   │   ├── nodes.py        # Cada passo do agente
│   │   ├── state.py        # Estado que circula entre nós
│   │   └── prompts.py      # Prompts para o LLM
│   ├── api/
│   │   └── routes.py       # Endpoint /ask, /health, /cache/status
│   ├── services/
│   │   ├── bigquery_service.py      # Consultas ao BigQuery
│   │   ├── llm_service.py           # Chamadas à OpenAI
│   │   └── analytics_read_service.py # Lógica de leitura
│   ├── tools/              # ← Tools disponíveis para o agente
│   │   ├── performance_tools.py
│   │   ├── revenue_tools.py
│   │   └── traffic_tools.py
│   ├── repositories/       # Camada de acesso a dados
│   └── core/               # Configurações centralizadas
├── scripts/
│   ├── sync_bigquery_cache.py      # Sincroniza cache local
│   └── validate_real_services.py   # Testa BigQuery e OpenAI
├── data/
│   └── glacier_cache.db            # SQLite local
├── frontend/               # Next.js UI (dashboard + chat)
├── tests/                  # Testes unitários
└── requirements.txt        # Dependências Python
```


## 📝 Licença

MIT
