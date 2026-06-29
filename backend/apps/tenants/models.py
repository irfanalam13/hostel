import random
import re
import string
from decimal import Decimal
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.utils import timezone
from apps.common.models import TimeStampedModel

HOSTEL_CODE_RE = re.compile(r"^HTL-[A-Z0-9]{8}$")



class Plan(TimeStampedModel):
    name = models.CharField(max_length=50)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_students = models.IntegerField(default=200)
    max_rooms = models.IntegerField(default=50)

    # --- Public / marketing presentation (drives the landing-page pricing) ---
    description = models.CharField(max_length=200, blank=True, default="")
    # A plain list of feature bullet strings, e.g. ["Up to 50 beds", ...].
    features = models.JSONField(default=list, blank=True)
    period = models.CharField(max_length=40, blank=True, default="per hostel / month")
    currency = models.CharField(max_length=8, blank=True, default="Rs.")
    cta_label = models.CharField(max_length=40, blank=True, default="Get started")
    cta_href = models.CharField(max_length=200, blank=True, default="/signup")
    is_featured = models.BooleanField(default=False, help_text="Highlight as 'Most popular'.")
    is_public = models.BooleanField(default=True, help_text="Show on the public landing page.")
    sort_order = models.IntegerField(default=0)

    # --- Discount (configured from the admin panel) ---
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="0–100. Percentage off the monthly price while the discount is active.",
    )
    discount_label = models.CharField(
        max_length=60, blank=True, default="",
        help_text="Optional badge text, e.g. 'Launch offer'. Defaults to 'N% off'.",
    )
    discount_active = models.BooleanField(default=False)
    discount_until = models.DateField(
        null=True, blank=True, help_text="Optional expiry; the discount stops applying after this date.",
    )

    class Meta:
        ordering = ["sort_order", "price_monthly", "name"]

    def __str__(self):
        return self.name

    @property
    def discount_live(self) -> bool:
        """Whether the configured discount currently applies."""
        if not self.discount_active or (self.discount_percent or 0) <= 0:
            return False
        if self.discount_until and self.discount_until < timezone.localdate():
            return False
        return True

    @property
    def discounted_price(self) -> Decimal:
        """Effective monthly price after any live discount."""
        if not self.discount_live:
            return self.price_monthly
        factor = (Decimal("100") - Decimal(self.discount_percent)) / Decimal("100")
        return (self.price_monthly * factor).quantize(Decimal("0.01"))


def generate_hostel_code():
    alphabet = string.ascii_uppercase + string.digits
    return "HTL-" + "".join(random.choices(alphabet, k=8))


class Hostel(TimeStampedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=12, unique=True, db_index=True, blank=True)  # official Hostel ID

    address = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    owner_name = models.CharField(max_length=80, blank=True, default="")

    is_active = models.BooleanField(default=True)

    # SaaS settings and subscription basics
    settings = models.JSONField(default=dict, blank=True)
    plan_name = models.CharField(max_length=50, default="basic")
    subscription_active_until = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original_code = Hostel.objects.filter(pk=self.pk).values_list("code", flat=True).first()
            if original_code:
                self.code = original_code
        if not self.code:
            code = generate_hostel_code()
            while Hostel.objects.filter(code=code).exists():
                code = generate_hostel_code()
            self.code = code
        self.code = self.code.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"
    
class Subscription(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")  # active/cancelled/expired
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)


class Testimonial(TimeStampedModel):
    """
    A customer review of the platform. Anyone can submit one (it lands
    unapproved); an admin then "purifies" the pool — approving the genuine ones
    (which count toward the public rating stats) and featuring the best few to
    appear as cards in the landing-page testimonials section.
    """
    author_name = models.CharField(max_length=120)
    author_role = models.CharField(
        max_length=120, blank=True, default="",
        help_text="e.g. 'Warden, City Girls' Hostel'.",
    )
    rating = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    quote = models.TextField()

    # --- Moderation / curation (the "purify" step, done from the admin) ---
    is_approved = models.BooleanField(
        default=False, help_text="Approved reviews count toward the public rating stats.",
    )
    is_featured = models.BooleanField(
        default=False, help_text="Featured reviews appear as cards on the landing page.",
    )
    sort_order = models.IntegerField(default=0)
    source = models.CharField(max_length=40, blank=True, default="web")

    class Meta:
        ordering = ["sort_order", "-created_at"]

    def __str__(self):
        return f"{self.author_name} ({self.rating}★)"


def testimonial_stats():
    """
    Aggregate rating metrics over all *approved* reviews, for the landing page:

      - total                 number of approved reviews
      - average_rating        mean rating, 1 decimal (e.g. 4.6)
      - rating_percent        average as a percentage of 5 ("overall rating")
      - appreciation_percent  share of reviews rated 4★ or higher ("appreciate")
    """
    approved = Testimonial.objects.filter(is_approved=True)
    total = approved.count()
    if not total:
        return {
            "total": 0,
            "average_rating": 0.0,
            "rating_percent": 0,
            "appreciation_percent": 0,
            "positive": 0,
        }
    agg = approved.aggregate(avg=Avg("rating"), positive=Count("id", filter=Q(rating__gte=4)))
    avg = round(float(agg["avg"] or 0), 1)
    positive = agg["positive"] or 0
    return {
        "total": total,
        "average_rating": avg,
        "rating_percent": round(avg / 5 * 100),
        "appreciation_percent": round(positive / total * 100),
        "positive": positive,
    }
