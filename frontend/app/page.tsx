"use client";

import { useEffect, useState } from "react";

import {
  fetchBackendHealth,
  fetchCacheStatus,
  fetchDashboardOverview,
} from "@/lib/api";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { generateCopilotMessages } from "@/lib/copilot";
import type {
  BackendStatus,
  CacheStatusResponse,
  CopilotMessage,
  DashboardInsight,
  DashboardOverviewResponse,
  DashboardTrafficPoint,
} from "@/lib/types";

type DashboardState = "loading" | "ready" | "empty" | "offline" | "error";

type ContractCard = {
  bloco: string;
  campo: string;
  endpoint: string;
  origem: string;
  filtro: string;
};

const navItems = [
  { label: "Dashboard", active: true },
  { label: "Analytics", active: false },
  { label: "Relatorios", active: false },
  { label: "Configuracoes", active: false },
];

const CHANNEL_COLORS: Record<string, string> = {
  Display: "#38bdf8",
  Email: "#a78bfa",
  Facebook: "#fb7185",
  Organic: "#34d399",
  Search: "#facc15",
  Direct: "#f97316",
  Referral: "#94a3b8",
};

const CHANNEL_COLOR_ALIASES: Record<string, string> = {
  "Busca organica": "Organic",
  "Busca orgânica": "Organic",
  "Organic Search": "Organic",
  Direto: "Direct",
  "Facebook Ads": "Facebook",
};

const FALLBACK_CHANNEL_COLOR = "#cbd5e1";

const contractCards: ContractCard[] = [
  {
    bloco: "Total de usuarios",
    campo: "summary.totalUsers",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Total de pedidos",
    campo: "summary.totalOrders",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Receita",
    campo: "summary.revenue",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Taxa de conversao",
    campo: "summary.conversionRate",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Principal canal",
    campo: "summary.topChannel",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Taxa por canal",
    campo: "conversionByChannel",
    endpoint: "GET /api/dashboard/overview",
    origem: "Snapshot local / BigQuery",
    filtro: "period=30d, channel=all",
  },
  {
    bloco: "Trafego por origem",
    campo: "trafficBySource",
    endpoint: "GET /api/dashboard/overview",
    origem: "Serie temporal do BigQuery",
    filtro: "period=30d, channel=all",
  },
];

const backendStatusTone: Record<BackendStatus, string> = {
  checking: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  online: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
  offline: "border-rose-400/30 bg-rose-400/10 text-rose-100",
};

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Aguardando primeira sincronizacao";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(parsed);
}

function formatCompactNumber(value: number | null): string {
  if (value === null) {
    return "--";
  }

  return new Intl.NumberFormat("pt-BR", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatCurrency(value: number | null): string {
  if (value === null) {
    return "--";
  }

  if (value >= 1000) {
    return `US$ ${new Intl.NumberFormat("pt-BR", {
      notation: "compact",
      maximumFractionDigits: 1,
    }).format(value)}`;
  }

  return `US$ ${new Intl.NumberFormat("pt-BR", {
    maximumFractionDigits: 0,
  }).format(value)}`;
}

function formatPercent(value: number | null): string {
  if (value === null) {
    return "--";
  }

  return `${new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value)}%`;
}

function normalizeChannelLabel(value: string): string {
  const normalized: Record<string, string> = {
    "Organic Search": "Busca organica",
    Organic: "Busca organica",
    Direct: "Direto",
    "Social Media": "Redes sociais",
    "Facebook Ads": "Facebook Ads",
  };

  return normalized[value] ?? value;
}

function formatChartDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  }).format(parsed);
}

function formatTooltipDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(parsed);
}

function getTrafficChannels(trafficBySource: DashboardTrafficPoint[]): string[] {
  return Array.from(
    new Set(
      trafficBySource.flatMap((point) =>
        point.channels.map((channel) => channel.channel),
      ),
    ),
  );
}

function mapTrafficBySourceToChartData(trafficBySource: DashboardTrafficPoint[]) {
  return trafficBySource.map((point) => {
    const row: Record<string, string | number> = {
      date: formatChartDate(point.date),
    };

    for (const channel of point.channels) {
      row[channel.channel] = channel.visits;
    }

    return row;
  });
}

function getChannelColor(channel: string): string {
  const colorKey = CHANNEL_COLOR_ALIASES[channel] ?? channel;
  return CHANNEL_COLORS[colorKey] ?? FALLBACK_CHANNEL_COLOR;
}

function statusLabel(status: BackendStatus): string {
  if (status === "checking") {
    return "Carregando";
  }

  if (status === "online") {
    return "Online";
  }

  return "Offline";
}

function statusText(state: DashboardState): string {
  if (state === "loading") {
    return "Carregando dados";
  }

  if (state === "ready") {
    return "Dados sincronizados";
  }

  if (state === "empty") {
    return "Sem dados";
  }

  if (state === "offline") {
    return "Backend offline";
  }

  return "Erro na consulta";
}

function insightTone(type: DashboardInsight["type"]): string {
  if (type === "warning") {
    return "border-l-rose-400";
  }

  if (type === "success") {
    return "border-l-emerald-400";
  }

  return "border-l-sky-300";
}

function FilterChip({
  label,
  value,
  accent = "default",
}: {
  label: string;
  value: string;
  accent?: "default" | "primary" | "tertiary";
}) {
  const accentClass =
    accent === "primary"
      ? "border-sky-400/30 bg-sky-400/10 text-sky-100"
      : accent === "tertiary"
        ? "border-violet-400/30 bg-violet-400/10 text-violet-100"
        : "border-white/10 bg-white/5 text-slate-200";

  return (
    <div
      className={`glass-panel flex min-w-[144px] flex-col gap-1 rounded-2xl px-3 py-2 ${accentClass}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
        {label}
      </span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function KpiCard({
  label,
  value,
  helper,
  accent,
}: {
  label: string;
  value: string;
  helper: string;
  accent: string;
}) {
  return (
    <div className="glass-panel rounded-[22px] p-5">
      <div className="flex items-start justify-between gap-4">
        <div
          className={`flex h-10 w-10 items-center justify-center rounded-xl bg-slate-900/70 text-sm font-semibold ${accent}`}
        >
          {label.slice(0, 1).toUpperCase()}
        </div>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-400">
          contrato real
        </span>
      </div>
      <p className="mt-5 text-sm font-medium text-slate-400">{label}</p>
      <p className="mt-2 text-4xl font-semibold tracking-tight text-slate-50">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{helper}</p>
    </div>
  );
}

function buildTrafficPath(
  values: number[],
  chartWidth: number,
  chartHeight: number,
  maxValue: number,
): string {
  if (values.length === 0) {
    return "";
  }

  const stepX = values.length > 1 ? chartWidth / (values.length - 1) : 0;
  return values
    .map((value, index) => {
      const x = index * stepX;
      const y = chartHeight - (value / maxValue) * chartHeight;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    })
    .join(" ");
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function TrafficBySourceChart({
  trafficBySource,
}: {
  trafficBySource: DashboardTrafficPoint[];
}) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const chartData = mapTrafficBySourceToChartData(trafficBySource);
  const channels = getTrafficChannels(trafficBySource);

  if (chartData.length === 0 || channels.length === 0) {
    return (
      <div className="rounded-[20px] border border-dashed border-white/10 bg-slate-950/45 p-5">
        <p className="text-sm text-slate-300">
          Ainda nao ha serie temporal de trafego disponivel.
        </p>
        <p className="mt-2 text-sm text-slate-500">
          Quando o primeiro snapshot com dados diarios for processado, este grafico sera
          preenchido automaticamente.
        </p>
      </div>
    );
  }

  const chartWidth = 100;
  const chartHeight = 100;
  const pointCount = chartData.length;
  const stepX = pointCount > 1 ? chartWidth / (pointCount - 1) : 0;
  const maxValue = Math.max(
    1,
    ...chartData.flatMap((row) =>
      channels.map((channel) => Number(row[channel] ?? 0)),
    ),
  );
  const activeIndex = hoveredIndex ?? (pointCount === 1 ? 0 : null);
  const activeRow = activeIndex !== null ? chartData[activeIndex] : null;
  const activeX = activeIndex !== null ? activeIndex * stepX : 0;

  function handleMouseMove(event: React.MouseEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const relativeX = clamp((event.clientX - rect.left) / rect.width, 0, 1);
    const index =
      pointCount === 1 ? 0 : Math.round(relativeX * Math.max(pointCount - 1, 1));
    setHoveredIndex(index);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-xs text-slate-400">
        {channels.map((channel) => (
          <div key={channel} className="inline-flex items-center gap-2">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: getChannelColor(channel) }}
            />
            {normalizeChannelLabel(channel)}
          </div>
        ))}
      </div>

      <div
        className="relative h-[320px] overflow-hidden rounded-[20px] border border-white/6 bg-slate-950/45 p-4"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredIndex(null)}
      >
        <div className="absolute inset-0 grid grid-rows-4 px-4 py-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="border-t border-white/6" />
          ))}
        </div>

        <svg
          className="relative z-10 h-full w-full"
          preserveAspectRatio="none"
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        >
          {channels.map((channel) => {
            const values = chartData.map((row) => Number(row[channel] ?? 0));
            return (
              <g key={channel}>
                <path
                  d={buildTrafficPath(values, chartWidth, chartHeight, maxValue)}
                  fill="none"
                  stroke={getChannelColor(channel)}
                  strokeWidth="2.4"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity="0.92"
                />
                {pointCount === 1 ? (
                  <circle
                    cx={0}
                    cy={chartHeight - (values[0] / maxValue) * chartHeight}
                    r="2.8"
                    fill={getChannelColor(channel)}
                  />
                ) : null}
                {activeIndex !== null ? (
                  <circle
                    cx={activeX}
                    cy={chartHeight - (values[activeIndex] / maxValue) * chartHeight}
                    r="2.6"
                    fill={getChannelColor(channel)}
                    stroke="#0f172a"
                    strokeWidth="1.2"
                  />
                ) : null}
              </g>
            );
          })}
          {activeIndex !== null ? (
            <line
              x1={activeX}
              x2={activeX}
              y1={0}
              y2={chartHeight}
              stroke="rgba(148, 163, 184, 0.45)"
              strokeDasharray="2 3"
            />
          ) : null}
        </svg>

        {activeRow ? (
          <div
            className="pointer-events-none absolute top-4 z-20 w-56 rounded-2xl border border-sky-300/15 bg-slate-950/95 px-4 py-3 text-xs text-slate-300 shadow-2xl"
            style={{
              left: `clamp(1rem, calc(${(activeIndex ?? 0) / Math.max(pointCount - 1, 1)} * 100%), calc(100% - 15rem))`,
            }}
          >
            <p className="font-semibold text-slate-100">
              {formatTooltipDate(
                String(trafficBySource[activeIndex ?? 0]?.date ?? activeRow.date),
              )}
            </p>
            <div className="mt-3 space-y-2">
              {channels.map((channel) => (
                <div
                  key={channel}
                  className="flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ backgroundColor: getChannelColor(channel) }}
                    />
                    <span>{normalizeChannelLabel(channel)}</span>
                  </div>
                  <span className="font-semibold text-slate-100">
                    {new Intl.NumberFormat("pt-BR").format(
                      Number(activeRow[channel] ?? 0),
                    )}{" "}
                    visitas
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </div>

      <div className="flex justify-between px-2 text-xs text-slate-500">
        <span>{String(chartData[0]?.date ?? "--")}</span>
        <span>{String(chartData[Math.floor((chartData.length - 1) / 2)]?.date ?? "--")}</span>
        <span>{String(chartData[chartData.length - 1]?.date ?? "--")}</span>
      </div>
    </div>
  );
}

export default function HomePage() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");
  const [cacheStatus, setCacheStatus] = useState<CacheStatusResponse | null>(null);
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [dashboardState, setDashboardState] = useState<DashboardState>("loading");
  const [dashboardError, setDashboardError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      setDashboardState("loading");
      setDashboardError(null);

      try {
        const healthy = await fetchBackendHealth();
        if (!active) {
          return;
        }

        if (!healthy) {
          setBackendStatus("offline");
          setDashboardState("offline");
          setOverview(null);
          setCacheStatus(null);
          return;
        }

        setBackendStatus("online");

        const [cacheResult, overviewResult] = await Promise.allSettled([
          fetchCacheStatus(),
          fetchDashboardOverview(),
        ]);

        if (!active) {
          return;
        }

        if (cacheResult.status === "fulfilled") {
          setCacheStatus(cacheResult.value);
        } else {
          setCacheStatus(null);
        }

        if (overviewResult.status === "fulfilled") {
          setOverview(overviewResult.value);
          const hasRenderableData =
            overviewResult.value.summary !== null ||
            overviewResult.value.conversionByChannel.length > 0 ||
            overviewResult.value.trafficBySource.length > 0;
          setDashboardState(hasRenderableData ? "ready" : "empty");
          return;
        }

        setOverview(null);
        setDashboardState("error");
        setDashboardError(overviewResult.reason instanceof Error ? overviewResult.reason.message : "Nao foi possivel carregar o dashboard.");
      } catch {
        if (!active) {
          return;
        }

        setBackendStatus("offline");
        setDashboardState("offline");
        setOverview(null);
        setCacheStatus(null);
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, []);

  const summary = overview?.summary ?? null;
  const insights = overview?.insights ?? [];
  const conversionByChannel = overview?.conversionByChannel ?? [];
  const trafficBySource = overview?.trafficBySource ?? [];
  const lastSnapshotAt = overview?.lastSnapshotAt ?? cacheStatus?.last_snapshot_at ?? null;
  const copilotMessages =
    dashboardState === "ready" || dashboardState === "empty"
      ? generateCopilotMessages(overview)
      : [];

  return (
    <main className="min-h-screen pb-8">
      <nav className="sticky top-0 z-40 border-b border-sky-400/10 bg-slate-950/60 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 xl:px-6">
          <div className="flex items-center gap-8">
            <span className="text-xl font-semibold tracking-tight text-sky-300">Glacier AI</span>
            <div className="hidden items-center gap-6 md:flex">
              {navItems.map((item) => (
                <span
                  key={item.label}
                  className={`border-b-2 pb-1 text-sm font-medium transition-colors ${
                    item.active
                      ? "border-sky-400 text-sky-200"
                      : "border-transparent text-slate-400 hover:text-sky-100"
                  }`}
                >
                  {item.label}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 sm:flex">
              {["CL", "FL", "NT"].map((action) => (
                <button
                  key={action}
                  type="button"
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-[11px] font-semibold text-sky-200"
                >
                  {action}
                </button>
              ))}
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-gradient-to-br from-slate-700 to-slate-900 text-xs font-semibold text-slate-100">
              RG
            </div>
          </div>
        </div>
      </nav>

      <div className="relative mx-auto grid max-w-[1440px] gap-6 px-4 pt-6 xl:grid-cols-[minmax(0,1fr)_320px] xl:px-6">
        <div className="pointer-events-none absolute left-[18%] top-0 h-80 w-80 rounded-full bg-sky-400/12 blur-[120px]" />
        <div className="pointer-events-none absolute bottom-24 right-[20%] h-72 w-72 rounded-full bg-violet-400/10 blur-[120px]" />

        <section className="relative z-10 space-y-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-slate-50">
                Visao Geral de Analytics
              </h1>
              <p className="mt-2 text-sm text-slate-400">
                Metricas de performance e insights gerados por IA.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <FilterChip label="Periodo" value="Ultimos 30 dias" accent="primary" />
              <FilterChip label="Canal" value="Todos os canais" accent="tertiary" />
              <FilterChip label="Status" value={statusText(dashboardState)} />
            </div>
          </header>

          <div className="flex flex-wrap gap-3 text-xs text-slate-300">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 ${backendStatusTone[backendStatus]}`}
            >
              <span className="h-2 w-2 rounded-full bg-current" />
              Backend {statusLabel(backendStatus)}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5">
              Modo {cacheStatus?.data_source_mode ?? "cache indisponivel"}
            </span>
            <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-slate-400">
              Ultimo snapshot {formatDateTime(lastSnapshotAt)}
            </span>
          </div>

          {dashboardError ? (
            <div className="rounded-[20px] border border-rose-400/20 bg-rose-400/10 px-5 py-4 text-sm text-rose-100">
              {dashboardError}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-5">
            <KpiCard
              label="Total de usuarios"
              value={formatCompactNumber(summary?.totalUsers ?? null)}
              helper="GET /api/dashboard/overview -> summary.totalUsers"
              accent="text-sky-300"
            />
            <KpiCard
              label="Total de pedidos"
              value={formatCompactNumber(summary?.totalOrders ?? null)}
              helper="GET /api/dashboard/overview -> summary.totalOrders"
              accent="text-rose-300"
            />
            <KpiCard
              label="Receita"
              value={formatCurrency(summary?.revenue ?? null)}
              helper="GET /api/dashboard/overview -> summary.revenue"
              accent="text-violet-300"
            />
            <KpiCard
              label="Taxa de conversao"
              value={formatPercent(summary?.conversionRate ?? null)}
              helper="GET /api/dashboard/overview -> summary.conversionRate"
              accent="text-cyan-300"
            />
            <KpiCard
              label="Principal canal"
              value={summary ? normalizeChannelLabel(summary.topChannel) : "--"}
              helper="GET /api/dashboard/overview -> summary.topChannel"
              accent="text-slate-100"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.9fr)]">
            <div className="glass-panel rounded-[24px] p-6">
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-slate-50">Trafego por origem</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    GET /api/dashboard/overview -&gt; trafficBySource
                  </p>
                </div>
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-400">
                  serie real
                </span>
              </div>

              <TrafficBySourceChart trafficBySource={trafficBySource} />
            </div>

            <div className="glass-panel rounded-[24px] p-6">
              <div className="mb-6 flex items-center justify-between">
                <h3 className="text-base font-semibold text-slate-50">
                  Taxa de conversao por canal
                </h3>
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-400">
                  contract
                </span>
              </div>

              {conversionByChannel.length > 0 ? (
                <div className="space-y-6">
                  {conversionByChannel.map((item) => {
                    const width = `${Math.max(8, Math.min(item.conversionRate * 16, 100))}%`;

                    return (
                      <div key={item.channel} className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-300">
                            {normalizeChannelLabel(item.channel)}
                          </span>
                          <span className="font-semibold text-slate-100">
                            {formatPercent(item.conversionRate)}
                          </span>
                        </div>
                        <div className="h-3 overflow-hidden rounded-full bg-slate-800">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width,
                              backgroundColor: getChannelColor(item.channel),
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="rounded-[20px] border border-dashed border-white/10 bg-slate-950/45 p-5 text-sm text-slate-400">
                  Nenhuma taxa por canal disponivel ainda. O frontend deve renderizar
                  `conversionByChannel` quando o snapshot estiver pronto.
                </div>
              )}
            </div>
          </div>

          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-300/12 text-xs font-semibold text-violet-200">
                IA
              </span>
              <h3 className="text-lg font-semibold text-slate-50">Insights do dashboard</h3>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {insights.length > 0 ? (
                insights.map((insight) => (
                  <div
                    key={`${insight.type}-${insight.title}`}
                    className={`glass-panel rounded-[20px] border-l-2 p-5 ${insightTone(insight.type)}`}
                  >
                    <p className="text-sm font-semibold text-slate-50">{insight.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{insight.message}</p>
                  </div>
                ))
              ) : (
                <div className="glass-panel rounded-[20px] p-5 text-sm text-slate-400 md:col-span-3">
                  Nenhum insight disponivel ainda.
                </div>
              )}
            </div>
          </section>

          <section className="glass-panel rounded-[24px] p-6">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-50">Contrato de dados</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Cada bloco da tela agora aponta explicitamente para campo, endpoint e origem.
                </p>
              </div>
              <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-xs text-sky-100">
                painel de validacao
              </span>
            </div>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {contractCards.map((card) => (
                <div
                  key={card.bloco}
                  className="rounded-[20px] border border-white/10 bg-slate-950/45 p-5"
                >
                  <p className="text-sm font-semibold text-slate-50">{card.bloco}</p>
                  <div className="mt-4 space-y-2 text-xs leading-5 text-slate-400">
                    <p>Campo: {card.campo}</p>
                    <p>Endpoint: {card.endpoint}</p>
                    <p>Origem: {card.origem}</p>
                    <p>Filtro: {card.filtro}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </section>

        <aside className="relative z-10 xl:sticky xl:top-[88px] xl:self-start">
          <div className="glass-panel-elevated flex min-h-[720px] flex-col overflow-hidden rounded-[26px]">
            <CopilotPanel
              automaticMessages={copilotMessages}
              isLoading={dashboardState === "loading"}
            />
          </div>
        </aside>
      </div>
    </main>
  );
}
