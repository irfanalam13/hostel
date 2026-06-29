from django.db import migrations


FAQS = [
    ("Does it really work offline?",
     "Yes. The app is a Progressive Web App. You can keep admitting residents, recording payments and updating records during an outage — everything syncs automatically once you're back online."),
    ("Can I manage more than one hostel?",
     "Absolutely. The platform is multi-tenant, so owners and institutions can manage multiple properties with isolated data and per-property roles."),
    ("Is my data secure?",
     "Security is built in: role-based access control, strict tenant isolation, a complete audit log of sensitive actions, and encrypted offline storage on the device."),
    ("Can I import my existing data?",
     "Yes. You can bring in residents, rooms and fee structures, and export reports at any time — your data is always yours."),
    ("How do payments and billing work?",
     "Define your fee structures once and the system generates recurring invoices automatically. Record payments, issue receipts and reconcile dues without spreadsheets."),
    ("Do I need to install anything?",
     "No app store required. Open it in your browser and install it to your home screen in one tap for a native-like experience on any device."),
]

LAST_UPDATED = "Last updated June 2026"

PRIVACY_SECTIONS = [
    {"heading": "Overview", "body": ["This Privacy Policy explains how we collect, use, and protect information when you use our hostel management platform. We are committed to handling your data responsibly and transparently."]},
    {"heading": "Information we collect", "body": ["We collect the information needed to provide the service, including:"], "bullets": ["Account details such as name, email, and role within a hostel.", "Operational data you enter (residents, rooms, billing, payments, attendance).", "Technical data such as device, browser, and usage logs for security and reliability."]},
    {"heading": "How we use information", "body": ["We use your information to operate and improve the platform, secure your account, provide support, and meet legal obligations. We do not sell your personal data."]},
    {"heading": "Data storage & tenant isolation", "body": ["Each hostel's data is isolated from others. Data is stored securely and, where applicable, cached on your device for offline use using encrypted storage."]},
    {"heading": "Data retention", "body": ["We retain data for as long as your account is active or as needed to provide the service and comply with legal, audit, and regulatory requirements. You can request export or deletion at any time."]},
    {"heading": "Your rights", "body": ["Subject to applicable law, you may access, correct, export, or delete your personal data. Contact us to exercise these rights."]},
    {"heading": "Contact", "body": ["For privacy questions or requests, contact us via the details on our contact page."]},
]

TERMS_SECTIONS = [
    {"heading": "Acceptance of terms", "body": ["By accessing or using the platform, you agree to these Terms of Service. If you do not agree, do not use the service."]},
    {"heading": "Use of the service", "body": ["You agree to use the platform lawfully and responsibly. You must not:"], "bullets": ["Attempt to disrupt, reverse engineer, or gain unauthorised access to the service.", "Upload unlawful content or infringe the rights of others.", "Use the service in a way that violates applicable laws or regulations."]},
    {"heading": "Accounts & security", "body": ["You are responsible for safeguarding your account credentials and for all activity under your account. Notify us immediately of any unauthorised use."]},
    {"heading": "Subscriptions & billing", "body": ["Paid plans are billed according to the plan you select. Fees are non-refundable except where required by law. We may change pricing with reasonable notice."]},
    {"heading": "Availability", "body": ["We aim for high availability but do not guarantee uninterrupted service. The platform supports offline use, syncing your changes when connectivity is restored."]},
    {"heading": "Limitation of liability", "body": ["To the maximum extent permitted by law, we are not liable for indirect, incidental, or consequential damages arising from your use of the service."]},
    {"heading": "Changes to these terms", "body": ["We may update these Terms from time to time. Continued use of the service after changes take effect constitutes acceptance of the updated Terms."]},
]

SECURITY_SECTIONS = [
    {"heading": "Our approach", "body": ["Security is built into the platform from the ground up. We apply layered controls across the application, data, and infrastructure to protect your information."]},
    {"heading": "Access control", "body": ["We enforce least-privilege access throughout the product:"], "bullets": ["Role-based access control for every sensitive action.", "Strict tenant isolation so each hostel's data stays separate.", "Session protection and secure authentication."]},
    {"heading": "Data protection", "body": ["Your data is protected in transit and at rest:"], "bullets": ["Encrypted connections (HTTPS) for all traffic.", "Encrypted offline storage on the device for cached data.", "Content Security Policy, Trusted Types, and Subresource Integrity to harden the client."]},
    {"heading": "Auditing & monitoring", "body": ["Every sensitive action is recorded in a complete, exportable audit trail with configurable retention to support inspections and investigations."]},
    {"heading": "Resilience & recovery", "body": ["Scheduled backups and disaster-recovery tooling help ensure your data can be restored, with the offline-first design keeping you operational during outages."]},
    {"heading": "Reporting a vulnerability", "body": ["If you believe you've found a security issue, please contact us responsibly via our contact page so we can investigate and respond promptly."]},
]

LEGAL = [
    {"slug": "privacy", "eyebrow": "Legal", "title": "Privacy Policy", "description": "How we collect, use, and protect your information.", "sections": PRIVACY_SECTIONS},
    {"slug": "terms", "eyebrow": "Legal", "title": "Terms of Service", "description": "The terms that govern your use of the platform.", "sections": TERMS_SECTIONS},
    {"slug": "security", "eyebrow": "Trust", "title": "Security", "description": "How we keep your data safe — access control, encryption, auditing and recovery.", "sections": SECURITY_SECTIONS},
]

ABOUT = {
    "slug": "about",
    "eyebrow": "About us",
    "title": "The operating system for modern hostels",
    "description": "Hostel SaaS unifies admissions, beds, billing, payments and compliance so hostel teams can spend less time on paperwork and more time on people.",
    "body": [
        {"type": "prose", "heading": "Our mission", "paragraphs": [
            "Hostels are run on spreadsheets, register books and unreliable internet. We set out to replace that with a single, dependable platform — one that works on any device, even offline, and that any warden or finance officer can pick up in minutes.",
            "From a single private hostel to multi-campus institutions, our goal is the same: make day-to-day operations effortless and give owners a clear, real-time view of occupancy and collections.",
        ]},
        {"type": "cards", "items": [
            {"icon": "Target", "title": "Built for operators", "description": "Every feature comes from how hostels actually run — not how software thinks they should."},
            {"icon": "Heart", "title": "Calm by design", "description": "A fast, uncluttered interface that reduces busywork instead of adding to it."},
            {"icon": "Sparkles", "title": "Offline-first", "description": "Reliable even when the internet isn't — your front desk never stops working."},
            {"icon": "ShieldCheck", "title": "Secure & accountable", "description": "Tenant isolation, role-based access and a full audit trail, out of the box."},
        ]},
    ],
}


def seed(apps, schema_editor):
    Faq = apps.get_model("marketing", "Faq")
    LegalDocument = apps.get_model("marketing", "LegalDocument")
    SitePage = apps.get_model("marketing", "SitePage")

    for i, (q, a) in enumerate(FAQS):
        Faq.objects.get_or_create(question=q, defaults={"answer": a, "order": i, "is_published": True})

    for doc in LEGAL:
        LegalDocument.objects.get_or_create(
            slug=doc["slug"],
            defaults={
                "eyebrow": doc["eyebrow"], "title": doc["title"],
                "description": doc["description"], "last_updated": LAST_UPDATED,
                "sections": doc["sections"], "is_published": True,
            },
        )

    SitePage.objects.get_or_create(
        slug=ABOUT["slug"],
        defaults={
            "eyebrow": ABOUT["eyebrow"], "title": ABOUT["title"],
            "description": ABOUT["description"], "body": ABOUT["body"], "is_published": True,
        },
    )


def unseed(apps, schema_editor):
    apps.get_model("marketing", "Faq").objects.filter(question__in=[q for q, _ in FAQS]).delete()
    apps.get_model("marketing", "LegalDocument").objects.filter(slug__in=[d["slug"] for d in LEGAL]).delete()
    apps.get_model("marketing", "SitePage").objects.filter(slug=ABOUT["slug"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("marketing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
