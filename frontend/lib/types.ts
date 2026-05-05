export type BackendStatus = "checking" | "online" | "offline";

export type AskRequest = {
  question: string;
};

export type AskResponse = {
  answer: string;
  used_tool: string | null;
  data: Record<string, unknown> | Array<Record<string, unknown>> | null;
  error: string | null;
};

export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
};
