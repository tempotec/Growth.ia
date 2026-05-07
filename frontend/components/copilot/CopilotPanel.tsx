"use client";

import { useEffect, useRef, useState } from "react";
import { askQuestion } from "@/lib/api";
import type { ChatMessage, CopilotMessage } from "@/lib/types";

const SUGGESTED_QUESTIONS = [
  "Como foi o volume de usuários vindos de Search no último mês?",
  "Qual canal teve melhor performance e por quê?",
  "Qual canal gerou mais receita?",
  "Compare Search, Organic e Display.",
  "Existe algum canal com baixo desempenho?",
];
const OUT_OF_SCOPE_ERROR = "unsupported_intent";

type CopilotPanelProps = {
  automaticMessages: CopilotMessage[];
  isLoading: boolean;
};

export function CopilotPanel({ automaticMessages, isLoading }: CopilotPanelProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isSending, setIsSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll para a última mensagem
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chatMessages]);

  const handleSendQuestion = async (question: string) => {
    if (!question.trim() || isSending) return;

    // Adicionar mensagem do usuário
    const userMessageId = `user-${Date.now()}`;
    setChatMessages((prev) => [
      ...prev,
      {
        id: userMessageId,
        role: "user",
        content: question,
        status: "done",
      },
    ]);

    setInputValue("");
    setIsSending(true);

    // Adicionar loading
    const loadingId = `assistant-loading-${Date.now()}`;
    setChatMessages((prev) => [
      ...prev,
      {
        id: loadingId,
        role: "assistant",
        content: "Analisando dados...",
        status: "sending",
      },
    ]);

    try {
      const response = await askQuestion(question);

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
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendQuestion(inputValue);
    }
  };

  const hasMessages = chatMessages.length > 0;

  return (
    <div className="flex h-full flex-col bg-slate-900/40">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/8 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-300 to-violet-300 text-sm font-semibold text-slate-950">
            IA
            <span className="absolute -bottom-1 -right-1 h-3 w-3 rounded-full border-2 border-slate-950 bg-emerald-400" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-50">Copiloto</h2>
            <p className="text-[11px] text-slate-500">
              {hasMessages ? "Chat com agente" : "Faça uma pergunta"}
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-100">
          Ativo
        </span>
      </div>

      {/* Chat area or automatic summary */}
      <div className="flex-1 overflow-y-auto px-4 py-5">
        <div
          ref={scrollRef}
          className="custom-scrollbar flex h-full flex-col gap-4 overflow-y-auto pr-1"
        >
          {/* Mostrar sumário automático se não há mensagens de chat */}
          {!hasMessages && (
            <>
              <div className="mb-2 text-xs font-medium text-slate-500">
                Resumo automático do overview
              </div>
              {isLoading ? (
                <div className="rounded-[20px] border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
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
              <ChatMessageBubble key={message.id} message={message} />
            ))}
        </div>
      </div>

      {/* Input area */}
      <div className="border-t border-white/8 px-4 py-4">
        {/* Suggested questions */}
        {!hasMessages && (
          <>
            <p className="mb-3 text-xs font-medium text-slate-500">Perguntas sugeridas</p>
            <div className="mb-4 flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => handleSendQuestion(question)}
                  disabled={isSending}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-white/20 hover:bg-white/10 disabled:opacity-50"
                >
                  {question}
                </button>
              ))}
            </div>
          </>
        )}

        {/* Input field */}
        <div className="rounded-[20px] border border-white/10 bg-slate-950/60 p-2">
          <div className="flex items-end gap-2">
            <textarea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              placeholder="Faça uma pergunta sobre seus dados..."
              rows={1}
              className="min-h-[44px] flex-1 resize-none bg-transparent px-1 py-2 text-sm text-slate-50 outline-none placeholder:text-slate-600 disabled:opacity-50"
            />
            <button
              type="button"
              onClick={() => handleSendQuestion(inputValue)}
              disabled={isSending || !inputValue.trim()}
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white/5 text-xs font-semibold text-slate-300 transition-colors hover:bg-white/10 disabled:opacity-50"
              aria-label="Enviar pergunta"
            >
              →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AutomaticMessageBubble({ message }: { message: CopilotMessage }) {
  const bgColorClass =
    message.type === "success"
      ? "bg-emerald-400/10 border-emerald-400/20"
      : message.type === "warning"
        ? "bg-amber-400/10 border-amber-400/20"
        : "bg-white/5 border-white/10";

  const textColorClass =
    message.type === "success"
      ? "text-emerald-100"
      : message.type === "warning"
        ? "text-amber-100"
        : "text-slate-100";

  return (
    <div className={`rounded-[20px] border p-4 text-sm ${bgColorClass} ${textColorClass}`}>
      {message.title && <p className="mb-1 font-semibold">{message.title}</p>}
      <p>{message.content}</p>
    </div>
  );
}

function ChatMessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isError = message.status === "error";

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-xs rounded-[20px] bg-sky-500/20 px-4 py-2 text-sm text-slate-50">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-xs space-y-2">
        <div
          className={`rounded-[20px] px-4 py-2 text-sm ${
            isError
              ? "border border-rose-400/20 bg-rose-400/10 text-rose-100"
              : message.status === "sending"
                ? "border border-white/10 bg-white/5 text-slate-300 italic"
                : "border border-white/10 bg-white/5 text-slate-50"
          }`}
        >
          {message.content}
        </div>
        {message.toolUsed && !isError && (
          <div className="px-1 text-[11px] text-slate-400">
            <span className="text-slate-500">Tool:</span> {message.toolUsed}
          </div>
        )}
      </div>
    </div>
  );
}
