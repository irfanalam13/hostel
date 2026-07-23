import type { LegalSection } from "./components/LegalDocument";

/**
 * Long-form legal copy. This is reasonable, generic boilerplate — have it
 * reviewed by counsel and tailored to your jurisdiction before launch.
 */
export const LAST_UPDATED = "Last updated June 2026";

export const PRIVACY_SECTIONS: LegalSection[] = [
  {
    heading: "Overview",
    body: [
      "This Privacy Policy explains how we collect, use, and protect information when you use our hostel management platform. We are committed to handling your data responsibly and transparently.",
    ],
  },
  {
    heading: "Information we collect",
    body: ["We collect the information needed to provide the service, including:"],
    bullets: [
      "Account details such as name, email, and role within a hostel.",
      "Operational data you enter (residents, rooms, billing, payments, attendance).",
      "Technical data such as device, browser, and usage logs for security and reliability.",
    ],
  },
  {
    heading: "How we use information",
    body: [
      "We use your information to operate and improve the platform, secure your account, provide support, and meet legal obligations. We do not sell your personal data.",
    ],
  },
  {
    heading: "Data storage & tenant isolation",
    body: [
      "Each hostel's data is isolated from others. Data is stored securely and, where applicable, cached on your device for offline use using encrypted storage.",
    ],
  },
  {
    heading: "Data retention",
    body: [
      "We retain data for as long as your account is active or as needed to provide the service and comply with legal, audit, and regulatory requirements. You can request export or deletion at any time.",
    ],
  },
  {
    heading: "Your rights",
    body: [
      "Subject to applicable law, you may access, correct, export, or delete your personal data. Contact us to exercise these rights.",
    ],
  },
  {
    heading: "Contact",
    body: ["For privacy questions or requests, contact us via the details on our contact page."],
  },
];

export const TERMS_SECTIONS: LegalSection[] = [
  {
    heading: "Acceptance of terms",
    body: [
      "By accessing or using the platform, you agree to these Terms of Service. If you do not agree, do not use the service.",
    ],
  },
  {
    heading: "Use of the service",
    body: ["You agree to use the platform lawfully and responsibly. You must not:"],
    bullets: [
      "Attempt to disrupt, reverse engineer, or gain unauthorised access to the service.",
      "Upload unlawful content or infringe the rights of others.",
      "Use the service in a way that violates applicable laws or regulations.",
    ],
  },
  {
    heading: "Accounts & security",
    body: [
      "You are responsible for safeguarding your account credentials and for all activity under your account. Notify us immediately of any unauthorised use.",
    ],
  },
  {
    heading: "Subscriptions & billing",
    body: [
      "Paid plans are billed according to the plan you select. Fees are non-refundable except where required by law. We may change pricing with reasonable notice.",
    ],
  },
  {
    heading: "Availability",
    body: [
      "We aim for high availability but do not guarantee uninterrupted service. The platform supports offline use, syncing your changes when connectivity is restored.",
    ],
  },
  {
    heading: "Limitation of liability",
    body: [
      "To the maximum extent permitted by law, we are not liable for indirect, incidental, or consequential damages arising from your use of the service.",
    ],
  },
  {
    heading: "Changes to these terms",
    body: [
      "We may update these Terms from time to time. Continued use of the service after changes take effect constitutes acceptance of the updated Terms.",
    ],
  },
];

export const SECURITY_SECTIONS: LegalSection[] = [
  {
    heading: "Our approach",
    body: [
      "Security is built into the platform from the ground up. We apply layered controls across the application, data, and infrastructure to protect your information.",
    ],
  },
  {
    heading: "Access control",
    body: ["We enforce least-privilege access throughout the product:"],
    bullets: [
      "Role-based access control for every sensitive action.",
      "Strict tenant isolation so each hostel's data stays separate.",
      "Session protection and secure authentication.",
    ],
  },
  {
    heading: "Data protection",
    body: ["Your data is protected in transit and at rest:"],
    bullets: [
      "Encrypted connections (HTTPS) for all traffic.",
      "Encrypted offline storage on the device for cached data.",
      "Content Security Policy, Trusted Types, and Subresource Integrity to harden the client.",
    ],
  },
  {
    heading: "Auditing & monitoring",
    body: [
      "Every sensitive action is recorded in a complete, exportable audit trail with configurable retention to support inspections and investigations.",
    ],
  },
  {
    heading: "Resilience & recovery",
    body: [
      "Scheduled backups and disaster-recovery tooling help ensure your data can be restored, with the offline-first design keeping you operational during outages.",
    ],
  },
  {
    heading: "Reporting a vulnerability",
    body: [
      "If you believe you've found a security issue, please contact us responsibly via our contact page so we can investigate and respond promptly.",
    ],
  },
];
