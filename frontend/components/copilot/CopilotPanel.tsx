"use client";

import { useEffect, useRef, useState } from "react";
import { askQuestion } from "@/lib/api";
import type {
  BackendStatus,
  ChatMessage,
  ConversationMessage,
  CopilotMessage,
} from "@/lib/types";

const SUGGESTED_QUESTIONS = [
  "Como foi o volume de usuários vindos de Search no último mês?",
  "Qual canal teve melhor performance e por quê?",
  "Qual canal gerou mais receita?",
  "Compare Search, Organic e Display.",
  "Existe algum canal com baixo desempenho?",
];
const OUT_OF_SCOPE_ERROR = "unsupported_intent";
const CONVERSATION_HISTORY_LIMIT = 10;
const CONVERSATION_STORAGE_KEY = "glacier-ai:conversation-id";
const CHAT_STORAGE_PREFIX = "glacier-ai:chat:";
const NORMAL_STATUS_MESSAGES = [
  "Entendendo sua solicitacao...",
  "Consultando dados disponiveis...",
  "Finalizando...",
];
const THINKING_STATUS_MESSAGES = [
  "Entendendo sua solicitacao...",
  "Consultando dados disponiveis...",
  "Gerando primeira versao...",
  "Revisando qualidade da resposta...",
  "Ajustando para midia paga...",
  "Finalizando...",
];

type CopilotPanelProps = {
  automaticMessages: CopilotMessage[];
  backendStatus: BackendStatus;
  isLoading: boolean;
  variant?: "panel" | "full";
  showAutomaticSummary?: boolean;
};

export function CopilotPanel({
  automaticMessages,
  backendStatus,
  isLoading,
  variant = "panel",
  showAutomaticSummary = true,
}: CopilotPanelProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [thinkingMode, setThinkingMode] = useState(false);
  const [conversationId, setConversationId] = useState("default");
  const scrollRef = useRef<HTMLDivElement>(null);
  const isOnline = backendStatus === "online";
  const isFull = variant === "full";

  useEffect(() => {
    const storedConversationId = window.localStorage.getItem(CONVERSATION_STORAGE_KEY);
    const nextConversationId = storedConversationId || createConversationId();
    window.localStorage.setItem(CONVERSATION_STORAGE_KEY, nextConversationId);
    setConversationId(nextConversationId);

    const storedMessages = window.localStorage.getItem(
      `${CHAT_STORAGE_PREFIX}${nextConversationId}`,
    );
    if (!storedMessages) return;

    try {
      const parsedMessages = JSON.parse(storedMessages) as ChatMessage[];
      if (Array.isArray(parsedMessages)) {
        setChatMessages(parsedMessages);
      }
    } catch {
      window.localStorage.removeItem(`${CHAT_STORAGE_PREFIX}${nextConversationId}`);
    }
  }, []);

  useEffect(() => {
    if (conversationId === "default") return;

    const storageKey = `${CHAT_STORAGE_PREFIX}${conversationId}`;
    if (chatMessages.length === 0) {
      window.localStorage.removeItem(storageKey);
      return;
    }

    window.localStorage.setItem(storageKey, JSON.stringify(chatMessages));
  }, [chatMessages, conversationId]);

  // Auto-scroll para a última mensagem
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const handleSendQuestion = async (question: string) => {
    if (!question.trim() || isSending) return;

    const conversationHistory = buildConversationHistory(chatMessages);
    const selectedThinkingMode = thinkingMode;

    // Adicionar mensagem do usuário
    const userMessageId = `user-${Date.now()}`;
    setChatMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        role: "user",
        content: question,
        thinking_mode: selectedThinkingMode,
        status: "done",
      },
    ]);

    setInputValue("");
    setIsSending(true);

    // Adicionar loading
    const loadingId = `assistant-loading-${Date.now()}`;
    const statusMessages = selectedThinkingMode
      ? THINKING_STATUS_MESSAGES
      : NORMAL_STATUS_MESSAGES;
    let statusIndex = 0;
    const statusTimer = window.setInterval(() => {
      statusIndex = Math.min(statusIndex + 1, statusMessages.length - 1);
      setChatMessages((prev) =>
        prev.map((message) =>
          message.id === loadingId
            ? { ...message, content: statusMessages[statusIndex] }
            : message,
        ),
      );
    }, selectedThinkingMode ? 900 : 800);
    setChatMessages((prev) => [
      ...prev,
      {
        id: loadingId,
        role: "assistant",
        content: statusMessages[0],
        thinking_mode: selectedThinkingMode,
        status: "sending",
      },
    ]);

    try {
      const response = await askQuestion(question, {
        conversationId,
        thinkingMode: selectedThinkingMode,
        conversationHistory,
      });

      // Remover loading
      setChatMessages((prev) => prev.filter((msg) => msg.id !== loadingId));

      // Adicionar resposta
      if (response.error && response.error !== OUT_OF_SCOPE_ERROR) {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `assistant-error-${Date.now()}`,
            role: "assistant",
            content: `Erro: ${response.error}`,
            status: "error",
          },
        ]);
      } else {
        setChatMessages((prev) => [
          ...prev,
          {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: response.answer,
            toolUsed: response.error === OUT_OF_SCOPE_ERROR ? null : response.used_tool,
            thinking_mode: response.thinking_mode,
            intent: response.intent,
            traffic_source: response.traffic_source,
            mentioned_traffic_sources: response.mentioned_traffic_sources,
            date_range: response.date_range,
            analytics_context: response.analytics_context,
            status: "done",
          },
        ]);
      }
    } catch (error) {
      // Remover loading
      setChatMessages((prev) => prev.filter((msg) => msg.id !== loadingId));

      // Adicionar erro
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Não foi possível consultar o agente agora. Verifique se o backend está online.";

      setChatMessages((prev) => [
        ...prev,
        {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: errorMessage,
          status: "error",
        },
      ]);
    } finally {
      window.clearInterval(statusTimer);
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendQuestion(inputValue);
    }
  };

  const handleClearConversation = () => {
    if (isSending) return;
    const previousConversationId = conversationId;
    const nextConversationId = createConversationId();
    window.localStorage.removeItem(`${CHAT_STORAGE_PREFIX}${previousConversationId}`);
    window.localStorage.setItem(CONVERSATION_STORAGE_KEY, nextConversationId);
    setConversationId(nextConversationId);
    setChatMessages([]);
    setInputValue("");
  };

  const hasMessages = chatMessages.length > 0;
  const containerClass = isFull
    ? "flex min-h-[calc(100vh-8rem)] flex-col overflow-hidden rounded-[24px] border border-stone-200 bg-white/85 shadow-xl"
    : "sticky top-24 flex h-[calc(100vh-7rem)] flex-col overflow-hidden rounded-3xl border border-stone-200 bg-white/80 shadow-xl";

  return (
    <section className={containerClass}>
      {/* Header fixo */}
      <div className="shrink-0 flex items-center justify-between border-b border-borderSoft px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-pistachio/35 text-sm font-semibold text-ink">
            IA
            <span
              className={`absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-white ${
                isOnline ? "bg-lime-500" : "bg-red-500"
              }`}
              title={isOnline ? "Copiloto online" : "Copiloto offline"}
            />
          </div>
          <div>
            <h2 className="text-base font-semibold text-ink">Copiloto</h2>
            <p className="text-[11px] text-muted">
              {hasMessages ? "Chat com agente" : "Faça uma pergunta"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {hasMessages && (
            <button
              type="button"
              onClick={handleClearConversation}
              disabled={isSending}
              className="rounded-full border border-borderSoft bg-white/70 px-2.5 py-1 text-[11px] font-medium text-muted transition-colors hover:border-orange/50 hover:bg-cream disabled:opacity-50"
            >
              Limpar conversa
            </button>
          )}
          <span
            className={`inline-flex items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
              isOnline
                ? "border-lime-300 bg-lime-100 text-lime-800"
                : "border-red-300 bg-red-100 text-red-700"
            }`}
          >
            {isOnline ? "Ativo" : "Offline"}
          </span>
        </div>
      </div>

      {/* Área que rola */}
      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div
          ref={scrollRef}
          className="custom-scrollbar flex flex-col gap-4 pr-1"
        >
          {/* Mostrar sumário automático se não há mensagens de chat */}
          {!hasMessages && showAutomaticSummary && (
            <>
              <div className="mb-2 text-xs font-medium text-muted">
                Resumo automático do overview
              </div>
              {isLoading ? (
                <div className="rounded-[20px] border border-borderSoft bg-white/70 p-4 text-sm text-muted">
                  Aguardando resposta do backend para gerar insights determinísticos.
                </div>
              ) : (
                automaticMessages.map((message, index) => (
                  <AutomaticMessageBubble
                    key={`${message.role}-${index}-${message.content.slice(0, 24)}`}
                    message={message}
                  />
                ))
              )}
            </>
          )}

          {/* Chat messages */}
          {hasMessages &&
            chatMessages.map((message) => (
              <ChatMessageBubble key={message.id} message={message} variant={variant} />
            ))}
        </div>
      </div>

      {/* Input fixo embaixo */}
      <div className="shrink-0 border-t border-borderSoft bg-white/90 px-4 py-4">
        {/* Suggested questions */}
        {!hasMessages && (
          <>
            <p className="mb-3 text-xs font-medium text-muted">Perguntas sugeridas</p>
            <div className="mb-4 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => handleSendQuestion(question)}
                  disabled={isSending}
                  className="rounded-full border border-borderSoft bg-white/70 px-3 py-1.5 text-xs text-muted transition-colors hover:border-orange/50 hover:bg-cream disabled:opacity-50"
                >
                  {question}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Input field */}
        <div className="rounded-[20px] border border-borderSoft bg-white/80 p-2">
          <div className="mb-2 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => setThinkingMode((current) => !current)}
              disabled={isSending}
              aria-pressed={thinkingMode}
              className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-xs font-semibold transition-colors disabled:opacity-50 ${
                thinkingMode
                  ? "border-blueSoft/70 bg-blueSoft/25 text-ink"
                  : "border-borderSoft bg-white/70 text-muted hover:border-blueSoft/60 hover:text-ink"
              }`}
            >
              <span className="flex h-4 w-4 items-center justify-center rounded-full border border-current text-[10px]">
                P
              </span>
              Pensar
            </button>
            <span className="text-[11px] text-muted">
              {thinkingMode ? "Modo Pensar" : "Modo rapido"}
            </span>
          </div>

          <div className="flex items-end gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              placeholder="Faça uma pergunta sobre seus dados..."
              rows={1}
              className="min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2 text-sm text-ink outline-none placeholder:text-muted/70 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => handleSendQuestion(inputValue)}
              disabled={isSending || !inputValue.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-coral/15 text-xs font-semibold text-ink transition-colors hover:bg-coral/25 disabled:opacity-50"
              aria-label="Enviar pergunta"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

function createConversationId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `conversation-${crypto.randomUUID()}`;
  }

  return `conversation-${Date.now()}`;
}

function buildConversationHistory(messages: ChatMessage[]): ConversationMessage[] {
  return messages
    .filter(
      (message): message is ChatMessage & { role: "user" | "assistant" } =>
        (message.role === "user" || message.role === "assistant") &&
        message.status === "done" &&
        message.content.trim().length > 0,
    )
    .map((message) => {
      const historyMessage: ConversationMessage = {
        role: message.role,
        content: message.content,
      };

      if (message.intent) {
        historyMessage.intent = message.intent;
      }
      if (message.traffic_source) {
        historyMessage.traffic_source = message.traffic_source;
      }
      if (message.mentioned_traffic_sources?.length) {
        historyMessage.mentioned_traffic_sources = message.mentioned_traffic_sources;
      }
      if (message.date_range) {
        historyMessage.date_range = message.date_range;
      }
      if (message.analytics_context) {
        historyMessage.analytics_context = message.analytics_context;
      }

      return historyMessage;
    })
    .slice(-CONVERSATION_HISTORY_LIMIT);
}

function AutomaticMessageBubble({ message }: { message: CopilotMessage }) {
  const bgColorClass =
    message.type === "success"
      ? "bg-pistachio/20 border-pistachio/70"
      : message.type === "warning"
        ? "bg-yellowStar/25 border-yellowStar/70"
        : "bg-white/70 border-borderSoft";

  const textColorClass =
    message.type === "success"
      ? "text-ink"
      : message.type === "warning"
        ? "text-ink"
        : "text-ink";

  return (
    <div className={`rounded-[20px] border p-4 text-sm ${bgColorClass} ${textColorClass}`}>
      {message.title && <p className="mb-1 font-semibold">{message.title}</p>}
      <p>{message.content}</p>
    </div>
  );
}

function ChatMessageBubble({
  message,
  variant,
}: {
  message: ChatMessage;
  variant: "panel" | "full";
}) {
  const isUser = message.role === "user";
  const isError = message.status === "error";
  const maxWidthClass = variant === "full" ? "max-w-[78%]" : "max-w-xs";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className={`${maxWidthClass} rounded-[20px] bg-blueSoft/30 px-4 py-2 text-sm text-ink`}>
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className={`${maxWidthClass} space-y-2`}>
        <div
          className={`rounded-[20px] px-4 py-2 text-sm ${
            isError
              ? "border border-coral/35 bg-coral/15 text-ink"
              : message.status === "sending"
                ? "border border-borderSoft bg-white/65 text-muted italic"
                : "border border-borderSoft bg-white/75 text-ink"
          }`}
        >
          {message.content}
        </div>
      </div>
    </div>
  );
}
