import type { ComponentType } from "react";
import {
  Building2,
  BookOpen,
  CalendarRange,
  FileBarChart,
  Landmark,
  LayoutDashboard,
  ListTree,
  ScrollText,
  Settings2,
  Target,
} from "lucide-react";

export type AccountingSection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the Accounting module sub-navigation. */
export const ACCOUNTING_SECTIONS: AccountingSection[] = [
  {
    id: "overview",
    label: "Overview",
    description: "Financial position and key ledger metrics",
    href: "/accounting",
    icon: LayoutDashboard,
  },
  {
    id: "accounts",
    label: "Chart of Accounts",
    description: "Ledger accounts grouped by type",
    href: "/accounting/accounts",
    icon: ListTree,
  },
  {
    id: "journals",
    label: "Journals",
    description: "Record, approve and post journal entries",
    href: "/accounting/journals",
    icon: BookOpen,
  },
  {
    id: "ledger",
    label: "Ledger",
    description: "General ledger with running balances",
    href: "/accounting/ledger",
    icon: ScrollText,
  },
  {
    id: "statements",
    label: "Statements",
    description: "Trial balance, P&L, balance sheet, cash flow",
    href: "/accounting/statements",
    icon: FileBarChart,
  },
  {
    id: "fiscal-years",
    label: "Fiscal Years",
    description: "Periods, opening balances and year-end close",
    href: "/accounting/fiscal-years",
    icon: CalendarRange,
  },
  {
    id: "assets",
    label: "Fixed Assets",
    description: "Asset register, depreciation and disposal",
    href: "/accounting/assets",
    icon: Building2,
  },
  {
    id: "budgets",
    label: "Budgets",
    description: "Plan and approve account budgets",
    href: "/accounting/budgets",
    icon: Target,
  },
  {
    id: "banking",
    label: "Banking",
    description: "Bank accounts and statement reconciliation",
    href: "/accounting/banking",
    icon: Landmark,
  },
  {
    id: "setup",
    label: "Setup",
    description: "Cost centers, branches, currencies and taxes",
    href: "/accounting/setup",
    icon: Settings2,
  },
];
