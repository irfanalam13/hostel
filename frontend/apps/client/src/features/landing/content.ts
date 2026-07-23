import {
  BarChart3,
  BedDouble,
  Bell,
  CalendarCheck,
  CreditCard,
  DoorOpen,
  FileText,
  Receipt,
  ShieldCheck,
  Users,
  UserCheck,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import type { FeatureItem, StatItem } from "./types";

/**
 * Single source of truth for all landing copy. Structured so it can later be
 * driven by the backend CMS endpoints without touching the components.
 */
export const BRAND = {
  name: "Hostel SaaS",
  tagline: "The operating system for modern hostels",
  description:
    "Manage residents, rooms, billing, payments and occupancy for your hostel — online and offline, from any device.",
} as const;

export const HERO = {
  badge: "Trusted by hostels, schools & universities",
  title: "Run your entire hostel from one calm, fast dashboard",
  subtitle:
    "Admissions, beds, billing, payments and compliance — unified in a single platform that works even when the internet doesn't. Built for owners, wardens and finance teams.",
} as const;

export const STATS: StatItem[] = [
  { value: "10k+", label: "Beds managed", to: 10000, suffix: "+" },
  { value: "99.9%", label: "Uptime", to: 99, suffix: ".9%" },
  { value: "60%", label: "Less admin time", to: 60, suffix: "%" },
  { value: "24/7", label: "Offline-ready" },
];

export const FEATURES: FeatureItem[] = [
  {
    icon: UserCheck,
    title: "Admissions & onboarding",
    description:
      "Capture applications, verify documents and onboard residents in minutes with guided, validated workflows.",
  },
  {
    icon: BedDouble,
    title: "Rooms & bed occupancy",
    description:
      "See every block, room and bed at a glance. Allocate, transfer and track vacancies in real time.",
  },
  {
    icon: Receipt,
    title: "Billing & invoicing",
    description:
      "Automate recurring rent, mess and utility charges with transparent, itemised invoices.",
  },
  {
    icon: CreditCard,
    title: "Payments & receipts",
    description:
      "Record and reconcile payments, issue instant receipts, and chase dues without spreadsheets.",
  },
  {
    icon: CalendarCheck,
    title: "Attendance & gate logs",
    description:
      "Track presence, leave and visitor movement with auditable in/out records for safety.",
  },
  {
    icon: BarChart3,
    title: "Reports & analytics",
    description:
      "Occupancy, revenue and collections dashboards that turn daily operations into decisions.",
  },
  {
    icon: WifiOff,
    title: "Works offline",
    description:
      "A full PWA: keep working through outages — changes sync automatically when you reconnect.",
  },
  {
    icon: ShieldCheck,
    title: "Security & audit trail",
    description:
      "Role-based access, tenant isolation and a complete audit log of every sensitive action.",
  },
  {
    icon: Bell,
    title: "Notices & notifications",
    description:
      "Broadcast notices and send push notifications to residents and staff, instantly.",
  },
];

export type Step = { title: string; description: string };

export const STEPS: Step[] = [
  {
    title: "Set up your hostel",
    description:
      "Add blocks, rooms and beds, configure fee structures, and invite your team — all in one place.",
  },
  {
    title: "Admit & allocate",
    description:
      "Onboard residents, assign beds and generate invoices automatically from your fee plans.",
  },
  {
    title: "Operate & collect",
    description:
      "Track attendance, record payments, broadcast notices and resolve complaints day to day.",
  },
  {
    title: "Measure & improve",
    description:
      "Watch occupancy and collections in live dashboards and export reports for stakeholders.",
  },
];

export type Audience = { icon: LucideIcon; title: string; description: string };

export const AUDIENCES: Audience[] = [
  {
    icon: DoorOpen,
    title: "Hostel owners",
    description: "Maximise occupancy and collections across one or many properties.",
  },
  {
    icon: Users,
    title: "Schools & universities",
    description: "Run boarding and campus hostels with institutional-grade controls.",
  },
  {
    icon: UserCheck,
    title: "Wardens & admins",
    description: "Handle day-to-day operations without paperwork or guesswork.",
  },
  {
    icon: FileText,
    title: "Finance departments",
    description: "Transparent billing, reconciliation and audit-ready reporting.",
  },
];

export type PricingTier = {
  name: string;
  price: string;
  period?: string;
  description: string;
  features: string[];
  cta: { label: string; href: string };
  featured?: boolean;
  /** Set when a discount is live: the pre-discount price, shown struck through. */
  originalPrice?: string;
  /** Set when a discount is live: badge text, e.g. "Launch offer" or "20% off". */
  discountLabel?: string;
};

export const PRICING: PricingTier[] = [
  {
    name: "Starter",
    price: "Free",
    description: "For a single small hostel getting organised.",
    features: [
      "Up to 50 beds",
      "Admissions & occupancy",
      "Basic billing & payments",
      "Offline PWA access",
      "Community support",
    ],
    cta: { label: "Get started", href: "/signup" },
  },
  {
    name: "Growth",
    price: "Custom",
    period: "per hostel / month",
    description: "For growing hostels that need automation and insights.",
    features: [
      "Unlimited beds",
      "Automated recurring billing",
      "Reports & analytics",
      "Attendance, gate & visitors",
      "Push notifications",
      "Priority support",
    ],
    cta: { label: "Request a demo", href: "#contact" },
    featured: true,
  },
  {
    name: "Enterprise",
    price: "Let's talk",
    period: "multi-property",
    description: "For institutions and multi-property operators.",
    features: [
      "Everything in Growth",
      "Multi-tenant management",
      "SSO & advanced roles",
      "Disaster recovery & backups",
      "Audit & compliance exports",
      "Dedicated success manager",
    ],
    cta: { label: "Contact sales", href: "#contact" },
  },
];

export type Testimonial = {
  quote: string;
  name: string;
  role: string;
  /** 1–5; defaults to 5 when omitted (e.g. static fallback copy). */
  rating?: number;
};

export const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      "We replaced three spreadsheets and a register book. Collections are up and month-end takes an hour, not a week.",
    name: "Priya Sharma",
    role: "Warden, City Girls' Hostel",
  },
  {
    quote:
      "The offline mode is a lifesaver. Our campus internet is unreliable, but the front desk never stops working.",
    name: "Anil Gurung",
    role: "Hostel Manager, Sunrise College",
  },
  {
    quote:
      "Occupancy and dues at a glance across all four blocks. I finally run the hostel from my phone.",
    name: "Rajesh Thapa",
    role: "Owner, Greenfield Hostels",
  },
];

export type ComplianceItem = { title: string; description: string };

export const COMPLIANCE: ComplianceItem[] = [
  {
    title: "Resident records & registers",
    description:
      "Maintain mandated resident registers, ID proofs and stay records in a tamper-evident, exportable format.",
  },
  {
    title: "Visitor & gate logging",
    description:
      "Auditable in/out logs for residents and visitors to satisfy safety and security requirements.",
  },
  {
    title: "Data protection & access control",
    description:
      "Tenant isolation, role-based permissions and encryption keep personal data private by default.",
  },
  {
    title: "Audit trail & retention",
    description:
      "Every sensitive action is logged with configurable retention to support inspections and audits.",
  },
];

export type Faq = { question: string; answer: string };

export const FAQS: Faq[] = [
  {
    question: "Does it really work offline?",
    answer:
      "Yes. The app is a Progressive Web App. You can keep admitting residents, recording payments and updating records during an outage — everything syncs automatically once you're back online.",
  },
  {
    question: "Can I manage more than one hostel?",
    answer:
      "Absolutely. The platform is multi-tenant, so owners and institutions can manage multiple properties with isolated data and per-property roles.",
  },
  {
    question: "Is my data secure?",
    answer:
      "Security is built in: role-based access control, strict tenant isolation, a complete audit log of sensitive actions, and encrypted offline storage on the device.",
  },
  {
    question: "Can I import my existing data?",
    answer:
      "Yes. You can bring in residents, rooms and fee structures, and export reports at any time — your data is always yours.",
  },
  {
    question: "How do payments and billing work?",
    answer:
      "Define your fee structures once and the system generates recurring invoices automatically. Record payments, issue receipts and reconcile dues without spreadsheets.",
  },
  {
    question: "Do I need to install anything?",
    answer:
      "No app store required. Open it in your browser and install it to your home screen in one tap for a native-like experience on any device.",
  },
];

export const FOOTER_LINKS = {
  Product: [
    { label: "Features", href: "/#features" },
    { label: "Pricing", href: "/#pricing" },
    { label: "FAQ", href: "/#faq" },
    { label: "Log in", href: "/login" },
  ],
  Company: [
    { label: "About", href: "/about" },
    { label: "Contact sales", href: "/#contact" },
    { label: "Request a demo", href: "/#contact" },
  ],
  Legal: [
    { label: "Privacy", href: "/privacy" },
    { label: "Terms", href: "/terms" },
    { label: "Security", href: "/security" },
  ],
} as const;
