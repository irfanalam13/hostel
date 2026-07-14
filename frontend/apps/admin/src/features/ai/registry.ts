import type { ComponentType } from "react";
import { BookOpen, LayoutDashboard, MessageSquare } from "lucide-react";

export type AiSection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the AI module sub-navigation. */
export const AI_SECTIONS: AiSection[] = [
  {
    id: "assistant",
    label: "Assistant",
    description: "Ask questions about your hostel in plain language",
    href: "/ai",
    icon: MessageSquare,
  },
  {
    id: "knowledge",
    label: "Knowledge Base",
    description: "Documents the assistant can cite (policies, manual, FAQs)",
    href: "/ai/knowledge",
    icon: BookOpen,
  },
  {
    id: "dashboard",
    label: "Dashboard",
    description: "AI usage, tokens, latency and model activity",
    href: "/ai/dashboard",
    icon: LayoutDashboard,
  },
];
