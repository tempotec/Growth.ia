import type {
  CopilotMessage,
  DashboardConversionPoint,
  DashboardOverviewResponse,
  DashboardTrafficPoint,
} from "@/lib/types";

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

function hasOverviewData(overview: DashboardOverviewResponse | null): boolean {
  if (!overview) {
    return false;
  }

  return (
    overview.summary !== null ||
    overview.conversionByChannel.length > 0 ||
    overview.trafficBySource.length > 0 ||
    overview.insights.length > 0
  );
}

function dedupeMessages(messages: CopilotMessage[]): CopilotMessage[] {
  const seen = new Set<string>();
  return messages.filter((message) => {
    const key = [
      message.role,
      message.type ?? "",
      message.title ?? "",
      message.content.trim().toLowerCase(),
    ].join("|");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function messagesFromBackendInsights(
  overview: DashboardOverviewResponse,
): CopilotMessage[] {
  return overview.insights.map((insight) => ({
    role: "assistant",
    type: insight.type,
    title: insight.title,
    content: insight.message,
    source: "backend_insight",
  }));
}

function getBestConversionMessage(
  conversionByChannel: DashboardConversionPoint[],
): CopilotMessage | null {
  if (conversionByChannel.length === 0) {
    return null;
  }

  const bestConversion = [...conversionByChannel].sort(
    (left, right) => right.conversionRate - left.conversionRate,
  )[0];

  return {
    role: "assistant",
    type: "success",
    title: "Maior taxa de conversao",
    content: `${normalizeChannelLabel(bestConversion.channel)} apresenta a maior taxa de conversao, com ${bestConversion.conversionRate.toFixed(1)}%.`,
    source: "frontend_rule",
  };
}

function getTrafficVolumeMessage(
  trafficBySource: DashboardTrafficPoint[],
): CopilotMessage | null {
  if (trafficBySource.length === 0) {
    return null;
  }

  const totals = new Map<string, number>();
  for (const point of trafficBySource) {
    for (const channel of point.channels) {
      totals.set(channel.channel, (totals.get(channel.channel) ?? 0) + channel.visits);
    }
  }

  if (totals.size === 0) {
    return null;
  }

  const [topChannel, visits] = [...totals.entries()].sort(
    (left, right) => right[1] - left[1],
  )[0];

  return {
    role: "assistant",
    type: "info",
    title: "Maior volume de trafego",
    content: `${normalizeChannelLabel(topChannel)} concentrou o maior volume de trafego no periodo, com ${new Intl.NumberFormat("pt-BR").format(visits)} visitas.`,
    source: "frontend_rule",
  };
}

function getTrafficTrendMessage(
  trafficBySource: DashboardTrafficPoint[],
): CopilotMessage | null {
  if (trafficBySource.length < 2) {
    return null;
  }

  const channels = Array.from(
    new Set(
      trafficBySource.flatMap((point) => point.channels.map((channel) => channel.channel)),
    ),
  );

  let strongestDeltaChannel: string | null = null;
  let strongestDeltaValue = 0;

  for (const channel of channels) {
    const firstValue =
      trafficBySource[0].channels.find((entry) => entry.channel === channel)?.visits ?? 0;
    const lastValue =
      trafficBySource[trafficBySource.length - 1].channels.find(
        (entry) => entry.channel === channel,
      )?.visits ?? 0;
    const delta = lastValue - firstValue;

    if (Math.abs(delta) > Math.abs(strongestDeltaValue)) {
      strongestDeltaValue = delta;
      strongestDeltaChannel = channel;
    }
  }

  if (!strongestDeltaChannel || strongestDeltaValue === 0) {
    return null;
  }

  if (strongestDeltaValue > 0) {
    return {
      role: "assistant",
      type: "success",
      title: "Canal em alta",
      content: `${normalizeChannelLabel(strongestDeltaChannel)} ganhou tracao entre o primeiro e o ultimo ponto da serie, com alta de ${new Intl.NumberFormat("pt-BR").format(strongestDeltaValue)} visitas.`,
      source: "frontend_rule",
    };
  }

  return {
    role: "assistant",
    type: "warning",
    title: "Canal em queda",
    content: `${normalizeChannelLabel(strongestDeltaChannel)} perdeu volume entre o primeiro e o ultimo ponto da serie, com queda de ${new Intl.NumberFormat("pt-BR").format(Math.abs(strongestDeltaValue))} visitas.`,
    source: "frontend_rule",
  };
}

export function generateCopilotMessages(
  overview: DashboardOverviewResponse | null,
): CopilotMessage[] {
  if (!hasOverviewData(overview)) {
    return [
      {
        role: "assistant",
        type: "info",
        title: "Sem dados suficientes",
        content:
          "Ainda nao ha dados suficientes para gerar uma analise. Assim que o primeiro snapshot for processado, os insights aparecerao aqui.",
        source: "system",
      },
    ];
  }

  if (!overview || overview.summary === null) {
    return [
      {
        role: "assistant",
        type: "info",
        title: "Overview incompleto",
        content:
          "O dashboard respondeu, mas ainda nao ha resumo consolidado suficiente para leitura automatica.",
        source: "system",
      },
    ];
  }

  const messages: CopilotMessage[] = [];

  if (overview.trafficBySource.length === 0) {
    messages.push({
      role: "assistant",
      type: "info",
      title: "Serie temporal indisponivel",
      content:
        "O resumo geral ja possui dados, mas a serie temporal de trafego ainda nao esta disponivel.",
      source: "frontend_rule",
    });
  }

  if (overview.summary.topChannel) {
    messages.push({
      role: "assistant",
      type: "success",
      title: "Melhor canal do periodo",
      content: `O canal com melhor desempenho no periodo e ${normalizeChannelLabel(overview.summary.topChannel)}.`,
      source: "frontend_rule",
    });
  }

  const bestConversionMessage = getBestConversionMessage(overview.conversionByChannel);
  if (bestConversionMessage) {
    messages.push(bestConversionMessage);
  }

  const trafficVolumeMessage = getTrafficVolumeMessage(overview.trafficBySource);
  if (trafficVolumeMessage) {
    messages.push(trafficVolumeMessage);
  }

  const trafficTrendMessage = getTrafficTrendMessage(overview.trafficBySource);
  if (trafficTrendMessage) {
    messages.push(trafficTrendMessage);
  }

  const merged = [
    ...messagesFromBackendInsights(overview),
    ...messages,
  ];

  const deduped = dedupeMessages(merged);
  if (deduped.length > 0) {
    return deduped;
  }

  return [
    {
      role: "assistant",
      type: "info",
      title: "Sem insight destacado",
      content:
        "Os dados carregaram, mas ainda nao ha sinal suficiente para destacar um insight deterministico.",
      source: "system",
    },
  ];
}
