"use client";

import { AiShell } from "@/features/ai/components/primitives";
import { KnowledgeBase } from "@/features/ai/components/KnowledgeBase";

export default function AiKnowledgePage() {
  return (
    <AiShell
      title="Knowledge Base"
      description="Documents the assistant can cite — policies, rules, the hostel manual, FAQs."
    >
      <KnowledgeBase />
    </AiShell>
  );
}
