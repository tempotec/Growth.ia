import type { BackendStatus as BackendStatusType } from "@/lib/types";

type BackendStatusProps = {
  status: BackendStatusType;
};

const statusMap: Record<BackendStatusType, { label: string; tone: string }> = {
  checking: {
    label: "Testando backend",
    tone: "bg-amber-100 text-amber-800 border-amber-200",
  },
  online: {
    label: "Backend online",
    tone: "bg-moss text-pine border-green-200",
  },
  offline: {
    label: "Backend offline",
    tone: "bg-rose-100 text-rose-700 border-rose-200",
  },
};

export function BackendStatus({ status }: BackendStatusProps) {
  const { label, tone } = statusMap[status];

  return (
    <div
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium ${tone}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" />
      {label}
    </div>
  );
}
