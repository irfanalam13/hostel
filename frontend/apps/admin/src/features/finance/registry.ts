import type { ComponentType } from "react";
import {
  BarChart3,
  CreditCard,
  FileText,
  GraduationCap,
  Percent,
  Receipt,
  RotateCcw,
  TrendingDown,
  TrendingUp,
  Wallet,
} from "lucide-react";

export type FinanceSection = {
  id: string;
  label: string;
  description: string;
  href: string;
  icon: ComponentType<{ className?: string }>;
};

/** Single source of truth for the Finance module sub-navigation. */
export const FINANCE_SECTIONS: FinanceSection[] = [
  {
    id: "overview",
    label: "Overview",
    description: "Revenue, expenses and cash-flow at a glance",
    href: "/finance",
    icon: Wallet,
  },
  {
    id: "invoices",
    label: "Invoices",
    description: "Raise, issue and track resident invoices",
    href: "/finance/invoices",
    icon: FileText,
  },
  {
    id: "payments",
    label: "Payments",
    description: "Collect, verify and reconcile payments",
    href: "/finance/payments",
    icon: CreditCard,
  },
  {
    id: "fees",
    label: "Fees",
    description: "Fee categories, structures and assignments",
    href: "/finance/fees",
    icon: Receipt,
  },
  {
    id: "expenses",
    label: "Expenses",
    description: "Record and approve operational expenses",
    href: "/finance/expenses",
    icon: TrendingDown,
  },
  {
    id: "income",
    label: "Income",
    description: "Log ancillary and non-fee income",
    href: "/finance/income",
    icon: TrendingUp,
  },
  {
    id: "refunds",
    label: "Refunds",
    description: "Request, approve and process refunds",
    href: "/finance/refunds",
    icon: RotateCcw,
  },
  {
    id: "discounts",
    label: "Discounts",
    description: "Manage discount schemes and eligibility",
    href: "/finance/discounts",
    icon: Percent,
  },
  {
    id: "scholarships",
    label: "Scholarships",
    description: "Scholarships and resident awards",
    href: "/finance/scholarships",
    icon: GraduationCap,
  },
  {
    id: "reports",
    label: "Reports",
    description: "Collections, P&L, dues and exports",
    href: "/finance/reports",
    icon: BarChart3,
  },
];
