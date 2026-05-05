import type { AskResponse } from "@/lib/types";

type ResponsePanelProps = {
  response: AskResponse | null;
  errorMessage: string | null;
};

export function ResponsePanel({ response, errorMessage }: ResponsePanelProps) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-4 shadow-panel">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Resposta atual</h2>
        <span className="text-xs text-slate-500">Contrato da V1</span>
      </div>

      {errorMessage ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {errorMessage}
        </div>
      ) : null}

      {response ? (
        <div className="space-y-4">
          <div className="rounded-2xl bg-slate-50 px-4 py-4">
            <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Answer
            </div>
            <p className="text-sm text-slate-800">{response.answer}</p>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 px-4 py-3">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                used_tool
              </div>
              <p className="text-sm text-slate-800">{response.used_tool ?? "null"}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 px-4 py-3">
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                error
              </div>
              <p className="text-sm text-slate-800">{response.error ?? "null"}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-slate-950 px-4 py-3 text-xs text-slate-100">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              data
            </div>
            <pre>{JSON.stringify(response.data, null, 2)}</pre>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-500">
          A resposta do backend aparecera aqui junto com used_tool, error e data.
        </div>
      )}
    </div>
  );
}
