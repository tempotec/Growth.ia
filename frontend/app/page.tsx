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
  { label: "Análises", active: false },
  { label: "Relatórios", active: false },
  { label: "Configurações", active: false },
];

const CHANNEL_COLORS: Record<string, string> = {
  Search: "#8FC4E8",
  "Organic Search": "#B8D979",
  Organic: "#B8D979",
  Facebook: "#F2634A",
  "Facebook Ads": "#F2634A",
  Email: "#FFD36A",
  Direct: "#F79A3E",
  Display: "#8FB45A",
  Referral: "#6B7C89",
};

const CHANNEL_COLOR_ALIASES: Record<string, string> = {
  "Busca organica": "Organic",
  "Busca orgânica": "Organic",
  "Organic Search": "Organic",
  Direto: "Direct",
  "Facebook Ads": "Facebook",
};

const FALLBACK_CHANNEL_COLOR = "#6B7C89";

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

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Aguardando primeira sincronização";
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
    return "Sem conexão";
  }

  return "Erro na consulta";
}

function insightTone(type: DashboardInsight["type"]): string {
  if (type === "warning") {
    return "border-l-coral";
  }

  if (type === "success") {
    return "border-l-pistachioDark";
  }

  return "border-l-blueSoft";
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
      ? "border-blueSoft/60 bg-blueSoft/20 text-ink"
      : accent === "tertiary"
        ? "border-pistachio/70 bg-pistachio/20 text-ink"
        : "border-borderSoft bg-white/70 text-ink";

  return (
    <div
      className={`glass-panel flex min-w-[144px] flex-col gap-1 rounded-2xl px-3 py-2 ${accentClass}`}
    >
      <span className="text-[10px] font-semibold uppercase tracking-[0.22em] text-muted">
        {label}
      </span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function KpiCard({
  label,
  value,
  description,
  accent,
}: {
  label: string;
  value: string;
  description: string;
  accent: string;
}) {
  return (
    <div className="glass-panel rounded-[22px] p-5">
      <div className={`flex h-10 w-10 items-center justify-center rounded-xl bg-cream text-sm font-semibold ${accent}`}>
        {label.slice(0, 1).toUpperCase()}
      </div>
      <p className="mt-5 text-sm font-medium text-muted">{label}</p>
      <p className="mt-2 text-4xl font-semibold tracking-tight text-ink">{value}</p>
      <p className="mt-2 text-sm text-muted">{description}</p>
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
      <div className="rounded-[20px] border border-dashed border-borderSoft bg-cream/55 p-5">
        <p className="text-sm text-ink">
          Ainda não há série temporal de tráfego disponível.
        </p>
        <p className="mt-2 text-sm text-muted">
          Quando o primeiro snapshot com dados diários for processado, este gráfico será
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
      <div className="flex flex-wrap gap-3 text-xs text-muted">
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
        className="relative h-[320px] overflow-hidden rounded-[20px] border border-borderSoft bg-white/60 p-4"
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredIndex(null)}
      >
        <div className="absolute inset-0 grid grid-rows-4 px-4 py-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="border-t border-borderSoft/70" />
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
                    stroke="#FFF7E8"
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
              stroke="rgba(107, 124, 137, 0.45)"
              strokeDasharray="2 3"
            />
          ) : null}
        </svg>

        {activeRow ? (
          <div
            className="pointer-events-none absolute top-4 z-20 w-56 rounded-2xl border border-borderSoft bg-white/95 px-4 py-3 text-xs text-muted shadow-2xl"
            style={{
              left: `clamp(1rem, calc(${(activeIndex ?? 0) / Math.max(pointCount - 1, 1)} * 100%), calc(100% - 15rem))`,
            }}
          >
            <p className="font-semibold text-ink">
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
                  <span className="font-semibold text-ink">
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

      <div className="flex justify-between px-2 text-xs text-muted">
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
        setDashboardError(overviewResult.reason instanceof Error ? overviewResult.reason.message : "Não foi possível carregar o dashboard.");
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
      <nav className="sticky top-0 z-40 border-b border-borderSoft bg-cream/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 xl:px-6">
          <div className="flex items-center gap-8">
            <span className="text-xl font-semibold tracking-tight text-ink">Glacier AI</span>
            <div className="hidden items-center gap-6 md:flex">
              {navItems.map((item) => (
                <span
                  key={item.label}
                  className={`border-b-2 pb-1 text-sm font-medium transition-colors ${
                    item.active
                      ? "border-coral text-ink"
                      : "border-transparent text-muted hover:text-ink"
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
                  className="flex h-9 w-9 items-center justify-center rounded-full border border-borderSoft bg-white/70 text-[11px] font-semibold text-ink"
                >
                  {action}
                </button>
              ))}
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-borderSoft bg-pistachio/30 text-xs font-semibold text-ink">
              RG
            </div>
          </div>
        </div>
      </nav>

      <div className="relative mx-auto grid max-w-[1440px] gap-6 px-4 pt-6 xl:grid-cols-[minmax(0,1fr)_320px] xl:px-6">
        <section className="relative z-10 space-y-6">
          <header className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-4xl font-semibold tracking-tight text-ink">
                Visão Geral de Analytics
              </h1>
              <p className="mt-2 text-sm text-muted">
                Métricas de performance e insights gerados por IA.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <FilterChip label="Período" value="Últimos 30 dias" accent="primary" />
              <FilterChip label="Canal" value="Todos os canais" accent="tertiary" />
              <FilterChip label="Status" value={statusText(dashboardState)} />
            </div>
          </header>

          <div className="flex flex-wrap gap-3 text-xs text-ink">
            <span className="inline-flex items-center gap-2 rounded-full border border-borderSoft bg-white/70 px-3 py-1.5 text-muted">
              Último snapshot {formatDateTime(lastSnapshotAt)}
            </span>
          </div>

          {dashboardError ? (
            <div className="rounded-[20px] border border-coral/35 bg-coral/15 px-5 py-4 text-sm text-ink">
              {dashboardError}
            </div>
          ) : null}

          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-5">
            <KpiCard
              label="Total de usuários"
              value={formatCompactNumber(summary?.totalUsers ?? null)}
              description="Usuários identificados no período"
              accent="text-blueSoft"
            />
            <KpiCard
              label="Total de pedidos"
              value={formatCompactNumber(summary?.totalOrders ?? null)}
              description="Pedidos realizados no período"
              accent="text-coral"
            />
            <KpiCard
              label="Receita"
              value={formatCurrency(summary?.revenue ?? null)}
              description="Receita gerada pelos pedidos"
              accent="text-orange"
            />
            <KpiCard
              label="Taxa de conversão"
              value={formatPercent(summary?.conversionRate ?? null)}
              description="Relação entre pedidos e usuários"
              accent="text-pistachioDark"
            />
            <KpiCard
              label="Principal canal"
              value={summary ? normalizeChannelLabel(summary.topChannel) : "--"}
              description="Canal com melhor desempenho"
              accent="text-ink"
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.9fr)]">
            <div className="glass-panel rounded-[24px] p-6">
              <div className="mb-6">
                <h3 className="text-base font-semibold text-ink">Tráfego por origem</h3>
                <p className="mt-1 text-sm text-muted">
                  Série temporal do volume de visitas por canal
                </p>
              </div>

              <TrafficBySourceChart trafficBySource={trafficBySource} />
            </div>

            <div className="glass-panel rounded-[24px] p-6">
              <div className="mb-6">
                <h3 className="text-base font-semibold text-ink">
                  Taxa de conversão por canal
                </h3>
                <p className="mt-1 text-sm text-muted">
                  Percentual de usuários que converteram em pedido por canal
                </p>
              </div>

              {conversionByChannel.length > 0 ? (
                <div className="space-y-6">
                  {conversionByChannel.map((item) => {
                    const width = `${Math.max(8, Math.min(item.conversionRate * 16, 100))}%`;

                    return (
                      <div key={item.channel} className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted">
                            {normalizeChannelLabel(item.channel)}
                          </span>
                          <span className="font-semibold text-ink">
                            {formatPercent(item.conversionRate)}
                          </span>
                        </div>
                        <div className="h-3 overflow-hidden rounded-full bg-borderSoft/70">
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
                <div className="rounded-[20px] border border-dashed border-borderSoft bg-cream/55 p-5 text-sm text-muted">
                  Nenhuma taxa por canal disponível ainda. O frontend deve renderizar
                  dados quando o snapshot estiver pronto.
                </div>
              )}
            </div>
          </div>

          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-pistachio/25 text-xs font-semibold text-ink">
                IA
              </span>
              <h3 className="text-lg font-semibold text-ink">Insights do dashboard</h3>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {insights.length > 0 ? (
                insights.map((insight) => (
                  <div
                    key={`${insight.type}-${insight.title}`}
                    className={`glass-panel rounded-[20px] border-l-2 p-5 ${insightTone(insight.type)}`}
                  >
                    <p className="text-sm font-semibold text-ink">{insight.title}</p>
                    <p className="mt-2 text-sm leading-6 text-muted">{insight.message}</p>
                  </div>
                ))
              ) : (
                <div className="glass-panel rounded-[20px] p-5 text-sm text-muted md:col-span-3">
                  Nenhum insight disponível ainda.
                </div>
              )}
            </div>
          </section>

          <section>
            <details className="rounded-[24px] border border-borderSoft bg-white/70 p-6">
              <summary className="cursor-pointer text-sm font-semibold text-ink">
                Transparência dos dados (detalhes técnicos)
              </summary>

              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {contractCards.map((card) => (
                  <div
                    key={card.bloco}
                    className="rounded-[20px] border border-borderSoft bg-cream/45 p-5"
                  >
                    <p className="text-sm font-semibold text-ink">{card.bloco}</p>
                    <div className="mt-4 space-y-2 text-xs leading-5 text-muted">
                      <p>Campo: {card.campo}</p>
                      <p>Endpoint: {card.endpoint}</p>
                      <p>Origem: {card.origem}</p>
                      <p>Filtro: {card.filtro}</p>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          </section>
        </section>

        <aside className="relative z-10 xl:sticky xl:top-[88px] xl:self-start">
          <div className="glass-panel-elevated flex flex-col overflow-hidden rounded-[26px]">
            <CopilotPanel
              automaticMessages={copilotMessages}
              backendStatus={backendStatus}
              isLoading={dashboardState === "loading"}
            />
          </div>
        </aside>
      </div>
    </main>
  );
}
