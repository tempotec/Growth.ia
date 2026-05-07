import type {
  AskResponse,
  CacheStatusResponse,
  DashboardOverviewResponse,
} from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";
const USE_MOCK_API = process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

const MOCK_RESPONSE: AskResponse = {
  answer:
    "Organic foi o canal com melhor performance nos ultimos 30 dias, priorizando conversion_rate e usando revenue como desempate. Nao ha ROI real porque o dataset nao possui custo de midia.",
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

export async function askQuestion(question: string): Promise<AskResponse> {
  if (USE_MOCK_API) {
    await new Promise((resolve) => setTimeout(resolve, 600));
    return {
      ...MOCK_RESPONSE,
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
    body: JSON.stringify({ question }),
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
