export type BackendStatus = "checking" | "online" | "offline";

export type AskRequest = {
  question: string;
};

export type AskResponse = {
  answer: string;
  used_tool: string | null;
  data: Record<string, unknown> | Array<Record<string, unknown>> | null;
  error: string | null;
};

export type CacheStatusResponse = {
  status: "ok" | "warning";
  data_source_mode: string;
  last_sync_status: string | null;
  last_snapshot_at: string | null;
  cache_age_minutes: number | null;
  last_sync_started_at: string | null;
  last_sync_completed_at: string | null;
  last_sync_error_message: string | null;
};

export type DashboardOverviewSummary = {
  totalUsers: number;
  totalOrders: number;
  revenue: number;
  conversionRate: number;
  topChannel: string;
};

export type DashboardTrafficPoint = {
  date: string;
  channels: Array<{
    channel: string;
    visits: number;
  }>;
};

export type DashboardConversionPoint = {
  channel: string;
  conversionRate: number;
};

export type DashboardInsight = {
  type: "success" | "warning" | "info";
  title: string;
  message: string;
};

export type CopilotMessage = {
  role: "assistant" | "user";
  content: string;
  title?: string;
  type?: "success" | "warning" | "info";
  source?: "backend_insight" | "frontend_rule" | "system";
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolUsed?: string | null;
  status?: "sending" | "done" | "error";
};

export type DashboardOverviewResponse = {
  status: "online";
  period: string;
  channel: string;
  lastSnapshotAt: string | null;
  summary: DashboardOverviewSummary | null;
  trafficBySource: DashboardTrafficPoint[];
  conversionByChannel: DashboardConversionPoint[];
  insights: DashboardInsight[];
};
