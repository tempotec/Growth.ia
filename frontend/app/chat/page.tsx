"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { fetchBackendHealth } from "@/lib/api";
import type { BackendStatus } from "@/lib/types";

export default function ChatPage() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>("checking");

  useEffect(() => {
    let active = true;

    async function loadHealth() {
      try {
        const healthy = await fetchBackendHealth();
        if (!active) return;
        setBackendStatus(healthy ? "online" : "offline");
      } catch {
        if (!active) return;
        setBackendStatus("offline");
      }
    }

    void loadHealth();
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="min-h-screen pb-8">
      <nav className="sticky top-0 z-40 border-b border-borderSoft bg-cream/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-[1120px] items-center justify-between px-4 xl:px-6">
          <Link href="/" className="text-xl font-semibold tracking-tight text-ink">
            Glacier AI
          </Link>
          <div className="flex items-center gap-5 text-sm font-medium">
            <Link href="/" className="text-muted transition-colors hover:text-ink">
              Dashboard
            </Link>
            <span className="border-b-2 border-coral pb-1 text-ink">Chat</span>
          </div>
        </div>
      </nav>

      <div className="mx-auto max-w-[1120px] px-4 pt-6 xl:px-6">
        <CopilotPanel
          automaticMessages={[]}
          backendStatus={backendStatus}
          isLoading={backendStatus === "checking"}
          variant="full"
          showAutomaticSummary={false}
        />
      </div>
    </main>
  );
}
