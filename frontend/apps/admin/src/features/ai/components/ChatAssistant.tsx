"use client";

import React, { useEffect, useRef, useState } from "react";
import { Bot, FileText, Loader2, SendHorizontal, User, Wrench } from "lucide-react";
import { useToast } from "@hostel/ui";

import { aiApi } from "../api/ai.api";
import type { ChatMessage } from "../types/ai.types";

const SUGGESTIONS = [
  "How many beds are free right now?",
  "What are the outstanding dues this month?",
  "How much have we collected today?",
  "How many admissions are pending?",
];

let localId = 0;
const nextId = () => `local-${++localId}`;

export function ChatAssistant() {
  const toast = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [toolStatus, setToolStatus] = useState<string | null>(null);
  const conversationId = useRef<string | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming, toolStatus]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || streaming) return;
    setInput("");
    setStreaming(true);
    setToolStatus(null);

    const userMsg: ChatMessage = { id: nextId(), role: "user", content: message };
    const assistantId = nextId();
    setMessages((m) => [...m, userMsg, { id: assistantId, role: "assistant", content: "" }]);

    const patchAssistant = (fn: (prev: string) => string) =>
      setMessages((m) =>
        m.map((msg) => (msg.id === assistantId ? { ...msg, content: fn(msg.content) } : msg)),
      );

    try {
      const session = await aiApi.chat.start(message, conversationId.current);
      conversationId.current = session.conversation_id;

      await aiApi.chat.stream(session, {
        onToken: (delta) => {
          setToolStatus(null);
          patchAssistant((prev) => prev + delta);
        },
        onTool: (name, status) =>
          setToolStatus(status === "running" ? `Looking up ${name.replace(/_/g, " ")}…` : null),
        onDone: ({ content, sources }) => {
          setMessages((m) =>
            m.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    // Prefer the authoritative final content if streaming missed anything.
                    content: content && content.length > msg.content.length ? content : msg.content,
                    sources: sources && sources.length ? sources : msg.sources,
                  }
                : msg,
            ),
          );
        },
        onError: (msg) => {
          toast.error(msg || "The assistant hit an error.");
          patchAssistant((prev) => prev || "Sorry — I couldn't complete that request.");
        },
      });
    } catch (err) {
      const detail = (err as { data?: { message?: string } })?.data?.message;
      toast.error(detail || "Could not reach the AI assistant.");
      patchAssistant((prev) => prev || "Sorry — I couldn't reach the assistant.");
    } finally {
      setStreaming(false);
      setToolStatus(null);
    }
  }

  return (
    <div className="flex h-[calc(100vh-16rem)] min-h-[420px] flex-col rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)]">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--accent)]/10 text-[var(--accent)]">
              <Bot className="h-6 w-6" />
            </div>
            <h2 className="mt-3 text-base font-semibold text-[var(--foreground)]">
              Ask about your hostel
            </h2>
            <p className="mt-1 max-w-sm text-sm text-[var(--muted)]">
              I answer from your live workspace data — occupancy, dues, collections, students and
              more. I only ever see what your role can access.
            </p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-xl border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground-secondary)] transition hover:bg-[var(--background-secondary)]"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => <Bubble key={m.id} message={m} />)
        )}

        {toolStatus ? (
          <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <Wrench className="h-4 w-4 animate-pulse" />
            {toolStatus}
          </div>
        ) : null}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-end gap-2 border-t border-[var(--border)] p-3"
      >
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          rows={1}
          placeholder="Ask a question…"
          className="max-h-32 flex-1 resize-none rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent)]"
        />
        <button
          type="submit"
          disabled={streaming || !input.trim()}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-white transition disabled:opacity-40"
          aria-label="Send"
        >
          {streaming ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <SendHorizontal className="h-5 w-5" />
          )}
        </button>
      </form>
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${
          isUser
            ? "bg-[var(--background-secondary)] text-[var(--foreground-secondary)]"
            : "bg-[var(--accent)]/10 text-[var(--accent)]"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="max-w-[80%]">
        <div
          className={`whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
            isUser
              ? "bg-[var(--accent)] text-white"
              : "bg-[var(--background-secondary)] text-[var(--foreground)]"
          }`}
        >
          {message.content || (
            <span className="inline-flex items-center gap-1 text-[var(--muted)]">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> thinking…
            </span>
          )}
        </div>
        {message.sources && message.sources.length > 0 ? (
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium text-[var(--muted)]">Sources:</span>
            {message.sources.map((s) => (
              <span
                key={s.document_id}
                className="inline-flex items-center gap-1 rounded-md bg-[var(--background-secondary)] px-1.5 py-0.5 text-[11px] text-[var(--foreground-secondary)]"
              >
                <FileText className="h-3 w-3" />
                {s.title}
              </span>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
