"""Website section registry.

The public website is an ordered list of typed sections. Each type declares:

* ``label``      — what the builder UI calls it
* ``fields``     — a light schema ({name: kind}) the generic section editor
                   renders; kinds: text, textarea, image, url, boolean, number,
                   list (list of objects with their own field schema)
* ``default``    — the content a freshly scaffolded website starts with
* ``recommended``— counted as "missing" on the overview when absent

Content is stored as JSON and rendered by React (auto-escaped), so text is
plain text — no HTML is ever accepted or emitted, which is the XSS story.
Adding a new section type = one entry here + one renderer component; no
routing, model or API changes.
"""

SECTION_TYPES: dict[str, dict] = {
    "hero": {
        "label": "Hero",
        "recommended": True,
        "fields": {
            "headline": "text",
            "subtitle": "text",
            "description": "textarea",
            "image": "image",
            "video_url": "url",
            "badge": "text",                 # e.g. "Admissions open"
            "layout": "text",                # centered | split | full-bleed
            "buttons": {"kind": "list", "fields": {
                "label": "text", "href": "url", "style": "text",  # primary|outline|whatsapp
            }},
        },
        "default": {
            "headline": "",                   # scaffold fills with hostel name
            "subtitle": "A safe, comfortable place to stay",
            "description": "Welcome to our hostel. Book a visit or send us an inquiry below.",
            "image": "", "video_url": "", "badge": "Admissions open",
            "layout": "centered",
            "buttons": [
                {"label": "Send an inquiry", "href": "#inquiry", "style": "primary"},
                {"label": "Contact us", "href": "#contact", "style": "outline"},
            ],
        },
    },
    "about": {
        "label": "About",
        "recommended": True,
        "fields": {
            "title": "text",
            "story": "textarea",
            "mission": "textarea",
            "vision": "textarea",
            "message": "textarea",           # principal/owner message
            "message_author": "text",
            "why_choose_us": {"kind": "list", "fields": {"point": "text"}},
        },
        "default": {
            "title": "About us",
            "story": "Tell your hostel's story here — how it started and what makes it home.",
            "mission": "", "vision": "", "message": "", "message_author": "",
            "why_choose_us": [
                {"point": "Safe and secure environment"},
                {"point": "Homely food and clean rooms"},
            ],
        },
    },
    "stats": {
        "label": "Statistics",
        "recommended": True,
        "fields": {"items": {"kind": "list", "fields": {
            "label": "text", "value": "number", "suffix": "text",
        }}},
        "default": {"items": [
            {"label": "Students", "value": 100, "suffix": "+"},
            {"label": "Rooms", "value": 40, "suffix": ""},
            {"label": "Years of experience", "value": 5, "suffix": "+"},
        ]},
    },
    "facilities": {
        "label": "Facilities",
        "recommended": True,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "icon": "text", "description": "text",
        }}},
        "default": {"title": "Facilities", "items": [
            {"name": "WiFi", "icon": "wifi", "description": "High-speed internet"},
            {"name": "CCTV", "icon": "cctv", "description": "24/7 monitored premises"},
            {"name": "Laundry", "icon": "laundry", "description": "Weekly laundry service"},
            {"name": "Power backup", "icon": "power", "description": "Uninterrupted electricity"},
        ]},
    },
    "rooms": {
        "label": "Room types",
        "recommended": True,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "capacity": "number", "price_monthly": "number",
            "price_note": "text", "features": "textarea", "image": "image",
            "available": "boolean",
        }}},
        "default": {"title": "Rooms & pricing", "items": [
            {"name": "Shared room", "capacity": 3, "price_monthly": 8000,
             "price_note": "per month", "features": "Bed, locker, study table", "image": "",
             "available": True},
            {"name": "Single room", "capacity": 1, "price_monthly": 15000,
             "price_note": "per month", "features": "Bed, wardrobe, study table, attached bath",
             "image": "", "available": True},
        ]},
    },
    "gallery": {
        "label": "Gallery",
        "recommended": True,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "image": "image", "caption": "text",
        }}},
        "default": {"title": "Gallery", "items": []},
    },
    "dining": {
        "label": "Food & dining",
        "recommended": False,
        "fields": {
            "title": "text", "description": "textarea",
            "meals": {"kind": "list", "fields": {
                "meal": "text", "time": "text", "menu": "text",
            }},
        },
        "default": {"title": "Food & dining", "description": "", "meals": [
            {"meal": "Breakfast", "time": "7–9 AM", "menu": ""},
            {"meal": "Lunch", "time": "12–2 PM", "menu": ""},
            {"meal": "Dinner", "time": "7–9 PM", "menu": ""},
        ]},
    },
    "amenities": {
        "label": "Amenities",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {"name": "text"}}},
        "default": {"title": "Amenities", "items": [
            {"name": "Hot water"}, {"name": "Drinking water"}, {"name": "TV lounge"},
        ]},
    },
    "staff": {
        "label": "Our team",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "position": "text", "photo": "image", "description": "text",
        }}},
        "default": {"title": "Our team", "items": []},
    },
    "testimonials": {
        "label": "Testimonials",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "role": "text", "rating": "number",
            "feedback": "textarea", "photo": "image",
        }}},
        "default": {"title": "What residents say", "items": []},
    },
    "faq": {
        "label": "FAQ",
        "recommended": True,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "question": "text", "answer": "textarea",
        }}},
        "default": {"title": "Frequently asked questions", "items": [
            {"question": "What are the visiting hours?",
             "answer": "Visitors are welcome between 4 PM and 7 PM on weekdays."},
            {"question": "Is food included in the price?",
             "answer": "Yes — three meals a day are included in the monthly fee."},
        ]},
    },
    "notices": {
        "label": "Notice board",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "title": "text", "body": "textarea", "date": "text",
        }}},
        "default": {"title": "Notices", "items": []},
    },
    "events": {
        "label": "Events",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "date": "text", "description": "textarea",
            "image": "image", "registration_url": "url",
        }}},
        "default": {"title": "Events", "items": []},
    },
    "downloads": {
        "label": "Downloads",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "label": "text", "file": "url",
        }}},
        "default": {"title": "Downloads", "items": []},
    },
    "policies": {
        "label": "Policies",
        "recommended": False,
        "fields": {"title": "text", "items": {"kind": "list", "fields": {
            "name": "text", "body": "textarea",
        }}},
        "default": {"title": "Policies", "items": [
            {"name": "Hostel rules", "body": ""},
            {"name": "Visitor rules", "body": ""},
        ]},
    },
    "contact": {
        "label": "Contact & inquiry",
        "recommended": True,
        "fields": {
            "title": "text", "phone": "text", "email": "text", "address": "text",
            "office_hours": "text", "emergency_contact": "text",
            "map_embed_url": "url", "latitude": "text", "longitude": "text",
            "show_inquiry_form": "boolean",
        },
        "default": {
            "title": "Contact us", "phone": "", "email": "", "address": "",
            "office_hours": "Sun–Fri, 9 AM – 6 PM", "emergency_contact": "",
            "map_embed_url": "", "latitude": "", "longitude": "",
            "show_inquiry_form": True,
        },
    },
    "custom": {
        "label": "Custom section",
        "recommended": False,
        "fields": {"title": "text", "body": "textarea", "image": "image"},
        "default": {"title": "", "body": "", "image": ""},
    },
}

# The order a fresh website is scaffolded in.
DEFAULT_SECTION_ORDER = [
    "hero", "about", "stats", "facilities", "rooms", "gallery",
    "testimonials", "faq", "contact",
]


def default_content_for(section_type: str) -> dict:
    import copy

    return copy.deepcopy(SECTION_TYPES[section_type]["default"])


DEFAULT_THEME = {
    "primary_color": "#2563eb",
    "secondary_color": "#0f172a",
    "accent_color": "#f59e0b",
    "background": "#ffffff",
    "font": "system",           # system | serif | rounded
    "border_radius": "lg",      # none | md | lg | full
    "shadows": True,
    "animations": True,
    "button_style": "solid",    # solid | outline
    "header_style": "sticky",   # sticky | static
}

DEFAULT_SEO = {
    "meta_title": "",           # scaffold fills with hostel name
    "meta_description": "",
    "keywords": "",
    "og_image": "",
    "canonical_url": "",
    "robots": "index, follow",
}

DEFAULT_BRANDING = {
    "logo": "", "dark_logo": "", "favicon": "", "cover_image": "", "social_image": "",
}

DEFAULT_SOCIAL = {
    "facebook": "", "instagram": "", "linkedin": "", "tiktok": "",
    "youtube": "", "x": "", "whatsapp": "",
}

DEFAULT_NAVIGATION = {
    # Menu entries point at section anchors by default; custom URLs allowed.
    "items": [
        {"label": "About", "href": "#about", "visible": True},
        {"label": "Rooms", "href": "#rooms", "visible": True},
        {"label": "Gallery", "href": "#gallery", "visible": True},
        {"label": "FAQ", "href": "#faq", "visible": True},
        {"label": "Contact", "href": "#contact", "visible": True},
    ],
    "show_login": True,
}

DEFAULT_FOOTER = {
    "about_text": "",
    "quick_links": [
        {"label": "Staff login", "href": "/login"},
        {"label": "Student portal", "href": "/student"},
        {"label": "Parent portal", "href": "/parent"},
    ],
    "copyright": "",            # scaffold fills with hostel name
}
