const PROMPTS = [
  "Como foi o volume de usuarios vindos de Search no ultimo mes?",
  "Qual canal teve mais receita?",
  "Qual canal teve melhor performance e por que?",
];

type QuickPromptsProps = {
  onSelect: (prompt: string) => void;
};

export function QuickPrompts({ onSelect }: QuickPromptsProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Perguntas prontas</h2>
        <span className="text-xs text-slate-500">Atalho para smoke test</span>
      </div>
      <div className="grid gap-3">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onSelect(prompt)}
            className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm text-slate-700 transition hover:border-pine hover:bg-white"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
