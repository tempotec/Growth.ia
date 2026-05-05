import type { AskResponse } from "@/lib/types";

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

  const payload = (await response.json()) as AskResponse | { error?: string };
  if (!response.ok) {
    const message =
      "error" in payload && typeof payload.error === "string"
        ? payload.error
        : "Nao foi possivel consultar o backend.";
    throw new Error(message);
  }

  return payload as AskResponse;
}
