import { apiFetch } from "@hostel/api";

import type {
  AiConfig,
  AiDashboard,
  ChatSession,
  Conversation,
  ConversationDetail,
  KnowledgeDocument,
  StreamHandlers,
} from "../types/ai.types";

function f<T>(path: string, options: RequestInit = {}) {
  return apiFetch<T>(`/ai${path}`, options);
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

/**
 * Open the SSE stream to the ML service and dispatch parsed events.
 *
 * The platform's `apiFetch` only speaks JSON, so this is a purpose-built
 * primitive: a raw `fetch` reading `response.body` as a token stream. Auth is
 * the short-lived context token (Bearer) minted by `chat.start` — NOT the
 * session cookie — so the request is same-origin (via the /ai gateway path)
 * with no CSRF/credentials needed.
 */
async function streamChat(session: ChatSession, handlers: StreamHandlers): Promise<void> {
  const res = await fetch(session.stream_url, {
    method: "POST",
    headers: { Authorization: `Bearer ${session.token}` },
    signal: handlers.signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError?.(`Stream failed (${res.status})`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (frame: string) => {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
    }
    if (dataLines.length === 0) return;
    let data: Record<string, unknown> = {};
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch {
      return;
    }
    switch (event) {
      case "token":
        handlers.onToken?.(String(data.delta ?? ""));
        break;
      case "tool":
        handlers.onTool?.(String(data.name ?? ""), data.status === "done" ? "done" : "running");
        break;
      case "done":
        handlers.onDone?.({
          content: String(data.content ?? ""),
          model: data.model as string | undefined,
          provider: data.provider as string | undefined,
          sources: (data.sources as { title: string; document_id: string }[]) ?? [],
        });
        break;
      case "error":
        handlers.onError?.(String(data.message ?? "Unknown error"));
        break;
    }
  };

  // eslint-disable-next-line no-constant-condition
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (frame.trim()) dispatch(frame);
    }
  }
}

export const aiApi = {
  config: () => f<AiConfig>("/config/"),
  dashboard: () => f<AiDashboard>("/dashboard/"),

  conversations: {
    list: () => f<Conversation[]>("/conversations/"),
    retrieve: (id: string) => f<ConversationDetail>(`/conversations/${id}/`),
    remove: (id: string) => f<void>(`/conversations/${id}/`, { method: "DELETE" }),
  },

  knowledge: {
    list: () => f<KnowledgeDocument[]>("/knowledge/documents/"),
    /** Create from pasted text (JSON). */
    createText: (body: { title: string; content: string; visibility?: string }) =>
      f<KnowledgeDocument>("/knowledge/documents/", {
        method: "POST",
        ...json({ ...body, source_type: "TEXT" }),
      }),
    /** Create from an uploaded file (multipart). */
    createFile: (form: FormData) =>
      f<KnowledgeDocument>("/knowledge/documents/", { method: "POST", body: form }),
    remove: (id: string) => f<void>(`/knowledge/documents/${id}/`, { method: "DELETE" }),
    reingest: (id: string) =>
      f<{ status: string }>(`/knowledge/documents/${id}/reingest/`, { method: "POST" }),
  },

  chat: {
    /** Persist the user message + get the stream URL and context token. */
    start: (message: string, conversationId?: string) =>
      f<ChatSession>("/chat/", {
        method: "POST",
        ...json({ message, conversation_id: conversationId }),
      }),
    stream: streamChat,
  },
};
