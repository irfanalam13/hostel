"use client";

import React, { useState } from "react";
import { Mail, Phone, MapPin, Send, CheckCircle2 } from "lucide-react";
import { useToast } from "@/shared/ui/toast/ToastProvider";
import { Section } from "../components/Section";
import { SectionHeader } from "../components/SectionHeader";
import { Reveal } from "../components/Reveal";
import { submitLead } from "../site";
import { SECTION_IDS } from "../constants";

type Fields = { name: string; email: string; org: string; message: string };
type Errors = Partial<Record<keyof Fields, string>>;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validate(values: Fields): Errors {
  const errors: Errors = {};
  if (!values.name.trim()) errors.name = "Please enter your name.";
  if (!values.email.trim()) errors.email = "Please enter your email.";
  else if (!EMAIL_RE.test(values.email)) errors.email = "Enter a valid email address.";
  if (!values.message.trim()) errors.message = "Tell us a little about your hostel.";
  return errors;
}

const CONTACT_DETAILS = [
  { icon: Mail, label: "sales@hostelsaas.app", href: "mailto:sales@hostelsaas.app" },
  { icon: Phone, label: "+1 (000) 000-0000", href: "tel:+10000000000" },
  { icon: MapPin, label: "Available worldwide", href: undefined },
];

export function Contact() {
  const toast = useToast();
  const [values, setValues] = useState<Fields>({ name: "", email: "", org: "", message: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  const update = (key: keyof Fields) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setValues((v) => ({ ...v, [key]: e.target.value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const found = validate(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    const result = await submitLead({
      name: values.name.trim(),
      email: values.email.trim(),
      organization: values.org.trim(),
      message: values.message.trim(),
      kind: "demo",
    });
    setSubmitting(false);

    if (result.ok) {
      setDone(true);
      toast.success(result.message, "Request received");
      setValues({ name: "", email: "", org: "", message: "" });
    } else {
      toast.error(result.message, "Submission failed");
    }
  };

  const inputCls =
    "w-full rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-2.5 text-sm text-[var(--foreground)] placeholder:text-[var(--muted)] focus-visible:outline-none";

  return (
    <Section id={SECTION_IDS.contact} tone="muted" width="wide">
      <div className="grid gap-12 lg:grid-cols-2">
        <Reveal>
          <div>
            <SectionHeader
              align="left"
              eyebrow="Get in touch"
              title="Request a demo or talk to sales"
              description="Tell us about your hostel and we'll show you how to streamline admissions, billing and occupancy."
            />
            <ul className="mt-8 space-y-4">
              {CONTACT_DETAILS.map(({ icon: Icon, label, href }) => (
                <li key={label} className="flex items-center gap-3 text-sm text-[var(--foreground)]">
                  <span className="grid h-10 w-10 place-items-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent)]">
                    <Icon className="h-5 w-5" aria-hidden />
                  </span>
                  {href ? (
                    <a href={href} className="hover:text-[var(--accent)]">
                      {label}
                    </a>
                  ) : (
                    <span>{label}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>

        <Reveal delay={120}>
          {done ? (
            <div className="flex h-full flex-col items-center justify-center rounded-2xl border border-[var(--border)] bg-[var(--card)] p-10 text-center shadow-[var(--shadow-sm)]">
              <CheckCircle2 className="h-12 w-12 text-[var(--success)]" aria-hidden />
              <h3 className="mt-4 text-xl font-semibold text-[var(--foreground)]">Request received</h3>
              <p className="mt-2 text-sm text-[var(--foreground-secondary)]">
                Thanks for reaching out — our team will contact you shortly.
              </p>
              <button
                type="button"
                onClick={() => setDone(false)}
                className="mt-6 rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-2 text-sm font-medium text-[var(--foreground)] transition hover:bg-[var(--background-secondary)]"
              >
                Send another request
              </button>
            </div>
          ) : (
            <form
              onSubmit={onSubmit}
              noValidate
              className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-[var(--shadow-sm)] sm:p-8"
            >
              <div className="grid gap-5">
                <div>
                  <label htmlFor="c-name" className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
                    Full name <span className="text-[var(--error)]">*</span>
                  </label>
                  <input
                    id="c-name"
                    type="text"
                    value={values.name}
                    onChange={update("name")}
                    aria-invalid={!!errors.name}
                    aria-describedby={errors.name ? "c-name-err" : undefined}
                    className={inputCls}
                    placeholder="Jane Doe"
                  />
                  {errors.name && (
                    <p id="c-name-err" className="mt-1.5 text-xs text-[var(--error)]">
                      {errors.name}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="c-email" className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
                    Work email <span className="text-[var(--error)]">*</span>
                  </label>
                  <input
                    id="c-email"
                    type="email"
                    value={values.email}
                    onChange={update("email")}
                    aria-invalid={!!errors.email}
                    aria-describedby={errors.email ? "c-email-err" : undefined}
                    className={inputCls}
                    placeholder="jane@hostel.org"
                  />
                  {errors.email && (
                    <p id="c-email-err" className="mt-1.5 text-xs text-[var(--error)]">
                      {errors.email}
                    </p>
                  )}
                </div>

                <div>
                  <label htmlFor="c-org" className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
                    Hostel / institution
                  </label>
                  <input
                    id="c-org"
                    type="text"
                    value={values.org}
                    onChange={update("org")}
                    className={inputCls}
                    placeholder="Greenfield Hostels"
                  />
                </div>

                <div>
                  <label htmlFor="c-message" className="mb-1.5 block text-sm font-medium text-[var(--foreground)]">
                    Message <span className="text-[var(--error)]">*</span>
                  </label>
                  <textarea
                    id="c-message"
                    rows={4}
                    value={values.message}
                    onChange={update("message")}
                    aria-invalid={!!errors.message}
                    aria-describedby={errors.message ? "c-message-err" : undefined}
                    className={`${inputCls} resize-y`}
                    placeholder="How many beds do you manage? What would you like to improve?"
                  />
                  {errors.message && (
                    <p id="c-message-err" className="mt-1.5 text-xs text-[var(--error)]">
                      {errors.message}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  aria-busy={submitting || undefined}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-6 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[var(--accent-hover)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color-mix(in_srgb,var(--accent)_25%,transparent)] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Send className="h-4 w-4" aria-hidden />
                  {submitting ? "Sending…" : "Request a demo"}
                </button>
              </div>
            </form>
          )}
        </Reveal>
      </div>
    </Section>
  );
}
