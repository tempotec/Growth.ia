type ChatInputProps = {
  value: string;
  isLoading: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function ChatInput({
  value,
  isLoading,
  onChange,
  onSubmit,
}: ChatInputProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-panel">
      <label className="mb-2 block text-sm font-medium text-slate-600">
        Sua pergunta
      </label>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Digite uma pergunta sobre trafego, receita ou performance..."
        className="min-h-28 w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-pine focus:bg-white"
      />
      <div className="mt-4 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500">
          A V1 responde volume por origem, receita por canal e melhor performance por canal.
        </p>
        <button
          type="button"
          onClick={onSubmit}
          disabled={isLoading || !value.trim()}
          className="rounded-full bg-pine px-5 py-2 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {isLoading ? "Consultando..." : "Perguntar"}
        </button>
      </div>
    </div>
  );
}
