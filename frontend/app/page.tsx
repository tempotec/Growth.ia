"use client";

import { useEffect, useMemo, useState } from "react";

import { BackendStatus } from "@/components/backend-status";
import { ChatInput } from "@/components/chat-input";
import { MessageList } from "@/components/message-list";
import { QuickPrompts } from "@/components/quick-prompts";
import { ResponsePanel } from "@/components/response-panel";
import { askQuestion, fetchBackendHealth } from "@/lib/api";
import type { AskResponse, BackendStatus as BackendStatusType, ChatMessage } from "@/lib/types";

function createMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
    role,
    content,
  };
}

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [backendStatus, setBackendStatus] = useState<BackendStatusType>("checking");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const isHealthy = await fetchBackendHealth();
        if (active) {
          setBackendStatus(isHealthy ? "online" : "offline");
        }
      } catch {
        if (active) {
          setBackendStatus("offline");
        }
      }
    }

    void checkHealth();
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit() {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) {
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    setMessages((current) => [...current, createMessage("user", trimmedQuestion)]);

    try {
      const nextResponse = await askQuestion(trimmedQuestion);
      setResponse(nextResponse);
      setMessages((current) => [
        ...current,
        createMessage("assistant", nextResponse.answer),
      ]);
      setQuestion("");
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Nao foi possivel consultar o backend no momento.";
      setErrorMessage(message);
      setMessages((current) => [...current, createMessage("assistant", message)]);
    } finally {
      setIsLoading(false);
    }
  }

  const subtitle = useMemo(
    () =>
      "Uma casca minima para validar a experiencia do copiloto analitico enquanto o backend real e testado.",
    [],
  );

  return (
    <main className="min-h-screen px-4 py-10 md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="space-y-6">
          <header className="rounded-[2rem] border border-white/70 bg-white/80 p-6 shadow-panel backdrop-blur">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">
                  Growth.ia / Glacier AI
                </p>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink md:text-4xl">
                  Copiloto analitico para validar o fluxo real do backend
                </h1>
              </div>
              <BackendStatus status={backendStatus} />
            </div>
            <p className="max-w-3xl text-sm leading-6 text-slate-600">{subtitle}</p>
          </header>

          <QuickPrompts onSelect={setQuestion} />
          <ChatInput
            value={question}
            isLoading={isLoading}
            onChange={setQuestion}
            onSubmit={() => void handleSubmit()}
          />
          <MessageList messages={messages} />
        </section>

        <aside className="space-y-6">
          <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-panel">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-ink">Painel de resposta</h2>
              {isLoading ? (
                <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
                  Carregando
                </span>
              ) : null}
            </div>
            <ResponsePanel response={response} errorMessage={errorMessage} />
          </div>
        </aside>
      </div>
    </main>
  );
}
