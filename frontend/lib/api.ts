import type {
  AskRequest,
  AskResponse,
  CacheStatusResponse,
  ConversationMessage,
  DashboardOverviewResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

const MOCK_RESPONSE: AskResponse = {
  conversation_id: "mock-conversation",
  answer:
    "Organic foi o canal com melhor performance nos ultimos 30 dias, priorizando conversion_rate e usando revenue como desempate. Nao ha ROI real porque o dataset nao possui custo de midia.",
  thinking_mode: false,
  metadata: {
    tool_used: "get_channel_performance_summary",
    reflection_used: false,
    reflection_score: null,
    fallback_used: false,
    total_time_ms: 600,
    reflection_time_ms: null,
    tokens_used: null,
    cost_estimate: null,
  },
  used_tool: "get_channel_performance_summary",
  data: [
    {
      traffic_source: "Organic",
      users: 1000,
      orders: 80,
      revenue: 5500,
      conversion_rate: 0.08,
    },
  ],
  error: null,
  intent: "best_channel_performance",
  traffic_source: null,
  mentioned_traffic_sources: [],
  date_range: {
    start_date: "2026-04-08",
    end_date: "2026-05-07",
  },
  analytics_context: {
    last_intent: "best_channel_performance",
    last_channel: "Organic",
    last_compared_channels: [],
    last_metric_context: "channel_performance_summary",
    last_period: {
      start_date: "2026-04-08",
      end_date: "2026-05-07",
    },
    last_tool_result: {
      Organic: {
        users: 1000,
        orders: 80,
        revenue: 5500,
        conversion_rate: 0.08,
      },
    },
  },
};

const MOCK_CACHE_STATUS: CacheStatusResponse = {
  status: "ok",
  data_source_mode: "local_cache",
  last_sync_status: "success",
  last_snapshot_at: "2026-05-05T23:44:13Z",
  cache_age_minutes: 6,
  last_sync_started_at: "2026-05-05T23:40:00Z",
  last_sync_completed_at: "2026-05-05T23:44:00Z",
  last_sync_error_message: null,
};

const MOCK_DASHBOARD_OVERVIEW: DashboardOverviewResponse = {
  status: "online",
  period: "30d",
  channel: "all",
  lastSnapshotAt: "2026-05-05T23:44:13Z",
  summary: {
    totalUsers: 12500,
    totalOrders: 1248,
    revenue: 125400,
    conversionRate: 3.2,
    topChannel: "Busca organica",
  },
  trafficBySource: [
    {
      date: "2026-04-01",
      channels: [
        { channel: "Busca organica", visits: 842 },
        { channel: "Direto", visits: 420 },
        { channel: "Redes sociais", visits: 280 },
        { channel: "Facebook Ads", visits: 130 },
      ],
    },
  ],
  conversionByChannel: [
    { channel: "Busca organica", conversionRate: 4.8 },
    { channel: "Direto", conversionRate: 4.2 },
    { channel: "Redes sociais", conversionRate: 2.8 },
    { channel: "Facebook Ads", conversionRate: 1.2 },
  ],
  insights: [
    {
      type: "warning",
      title: "Queda em Facebook Ads",
      message:
        "Nos ultimos 7 dias, o custo por clique subiu e a conversao caiu para 1,2%.",
    },
  ],
};

export async function fetchBackendHealth(): Promise<boolean> {
  if (USE_MOCK_API) {
    return true;
  }

  const response = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    cache: "no-store",
  });
  return response.ok;
}

export async function fetchCacheStatus(): Promise<CacheStatusResponse> {
  if (USE_MOCK_API) {
    return MOCK_CACHE_STATUS;
  }

  const response = await fetch(`${API_BASE_URL}/cache/status`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Nao foi possivel consultar o status do cache.");
  }

  return (await response.json()) as CacheStatusResponse;
}

export async function fetchDashboardOverview(
  period = "30d",
  channel = "all",
): Promise<DashboardOverviewResponse> {
  if (USE_MOCK_API) {
    return MOCK_DASHBOARD_OVERVIEW;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/dashboard/overview?period=${encodeURIComponent(period)}&channel=${encodeURIComponent(channel)}`,
    {
      method: "GET",
      cache: "no-store",
    },
  );

  if (!response.ok) {
    throw new Error("Nao foi possivel consultar a visao geral do dashboard.");
  }

  return (await response.json()) as DashboardOverviewResponse;
}

type AskQuestionOptions = {
  conversationId?: string;
  thinkingMode?: boolean;
  conversationHistory?: ConversationMessage[];
};

export async function askQuestion(
  question: string,
  options: AskQuestionOptions | ConversationMessage[] = {},
): Promise<AskResponse> {
  const normalizedOptions = Array.isArray(options)
    ? { conversationHistory: options }
    : options;
  const conversationId = normalizedOptions.conversationId ?? "default";
  const thinkingMode = normalizedOptions.thinkingMode ?? false;
  const conversationHistory = normalizedOptions.conversationHistory ?? [];

  if (USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return {
      ...MOCK_RESPONSE,
      conversation_id: conversationId,
      thinking_mode: thinkingMode,
      metadata: {
        tool_used: MOCK_RESPONSE.metadata?.tool_used ?? null,
        reflection_used: thinkingMode,
        reflection_score: thinkingMode ? 8 : null,
        fallback_used: MOCK_RESPONSE.metadata?.fallback_used ?? false,
        total_time_ms: thinkingMode ? 1600 : 600,
        reflection_time_ms: thinkingMode ? 1000 : null,
        tokens_used: MOCK_RESPONSE.metadata?.tokens_used ?? null,
        cost_estimate: MOCK_RESPONSE.metadata?.cost_estimate ?? null,
      },
      answer:
        question.length > 0
          ? MOCK_RESPONSE.answer
          : "Pergunta vazia no modo mock.",
    };
  }

  const response = await fetch(`${API_BASE_URL}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      conversation_id: conversationId,
      message: question,
      question,
      thinking_mode: thinkingMode,
      conversation_history: conversationHistory,
    } satisfies AskRequest),
  });

  const payload = (await response.json()) as Partial<AskResponse> & { error?: string };
  if (!response.ok) {
    const message =
      typeof payload.answer === "string"
        ? payload.answer
        : typeof payload.error === "string"
          ? payload.error
        : "Nao foi possivel consultar o backend.";
    throw new Error(message);
  }

  return payload as AskResponse;
}
