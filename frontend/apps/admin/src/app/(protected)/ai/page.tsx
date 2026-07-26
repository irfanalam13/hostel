"use client";

import { AiShell } from "@/features/ai/components/primitives";
import { ChatAssistant } from "@/features/ai/components/ChatAssistant";

export default function AiPage() {
  return (
    <AiShell title="Assistant" description="Ask questions about your hostel in plain language.">
      <ChatAssistant />
    </AiShell>
  );
}
