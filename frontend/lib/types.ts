export type BackendStatus = "checking" | "online" | "offline";

export type SupportedIntent =
  | "traffic_volume_by_source"
  | "revenue_by_source"
  | "best_channel_performance"
  | "channel_performance_by_source"
  | "recommendation"
  | "out_of_scope";

export type ConversationDateRange = {
  start_date: string;
  end_date: string;
};

export type ConversationMessage = {
  role: "user" | "assistant";
  content: string;
  intent?: SupportedIntent | null;
  traffic_source?: string | null;
  date_range?: ConversationDateRange | null;
};

export type AskRequest = {
  question: string;
  conversation_history?: ConversationMessage[];
};

export type AskResponse = {
  answer: string;
  used_tool: string | null;
  data: Record<string, unknown> | Array<Record<string, unknown>> | null;
  error: string | null;
  intent: SupportedIntent | null;
  traffic_source: string | null;
  date_range: ConversationDateRange | null;
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
  totalConvertedUsers?: number;
  totalOrders: number;
  revenue: number;
  conversionRate: number;
  topChannel: string;
};

export type ChannelPerformance = {
  traffic_source: string;
  users: number;
  converted_users: number;
  orders: number;
  revenue: number;
  conversion_rate: number;
  start_date?: string | null;
  end_date?: string | null;
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
  intent?: SupportedIntent | null;
  traffic_source?: string | null;
  date_range?: ConversationDateRange | null;
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
