export type AiToolSpec = {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
};

export type AiConfig = {
  enabled: boolean;
  stream_base: string;
  tools: AiToolSpec[];
};

export type AiDashboard = {
  requests_today: number;
  tokens_today: number;
  avg_latency_ms: number;
  estimated_cost_usd: string;
  active_conversations: number;
  total_requests: number;
  model_usage: { model: string; requests: number }[];
};

export type ChatRole = "user" | "assistant" | "system" | "tool";

export type Source = { title: string; document_id: string };

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  tool_calls?: { name: string }[];
  sources?: Source[];
  provider?: string;
  model?: string;
  created_at?: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  source_type: "UPLOAD" | "TEXT" | "NOTICE" | "FAQ";
  content: string;
  visibility: "STAFF" | "ADMIN";
  status: "PENDING" | "INGESTING" | "READY" | "FAILED";
  error: string;
  chunk_count: number;
  embedding_model: string;
  created_at: string;
};

export type Conversation = {
  id: string;
  title: string;
  agent: string;
  provider: string;
  model: string;
  message_count: number;
  last_message_at: string | null;
  is_archived: boolean;
  created_at: string;
};

export type ConversationDetail = Conversation & { messages: ChatMessage[] };

export type ChatSession = {
  conversation_id: string;
  stream_url: string;
  token: string;
  expires_in: number;
};

/** Events emitted by the ML service over the SSE stream. */
export type StreamHandlers = {
  onToken?: (delta: string) => void;
  onTool?: (name: string, status: "running" | "done") => void;
  onDone?: (payload: {
    content: string;
    model?: string;
    provider?: string;
    sources?: Source[];
  }) => void;
  onError?: (message: string) => void;
  signal?: AbortSignal;
};
