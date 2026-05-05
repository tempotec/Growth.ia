import type { ChatMessage } from "@/lib/types";

type MessageListProps = {
  messages: ChatMessage[];
};

export function MessageList({ messages }: MessageListProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Historico da sessao</h2>
        <span className="text-xs text-slate-500">{messages.length} mensagens</span>
      </div>
      <div className="space-y-3">
        {messages.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
            Nenhuma mensagem ainda. Use uma pergunta pronta ou escreva a primeira consulta.
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`rounded-2xl px-4 py-3 text-sm ${
                message.role === "user"
                  ? "ml-8 bg-ink text-white"
                  : "mr-8 bg-mist text-slate-800"
              }`}
            >
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
                {message.role === "user" ? "Voce" : "Glacier AI"}
              </div>
              <p>{message.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
