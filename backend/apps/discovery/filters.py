import django_filters

from apps.tenants.models import Hostel


class DirectoryHostelFilter(django_filters.FilterSet):
    city = django_filters.CharFilter(field_name="discovery_profile__city", lookup_expr="iexact")
    district = django_filters.CharFilter(field_name="discovery_profile__district", lookup_expr="iexact")
    hostel_type = django_filters.CharFilter(field_name="discovery_profile__hostel_type", lookup_expr="iexact")
    min_rating = django_filters.NumberFilter(
        field_name="discovery_profile__average_rating", lookup_expr="gte"
    )
    amenity = django_filters.CharFilter(method="filter_amenity")

    class Meta:
        model = Hostel
        fields = ["city", "district", "hostel_type", "min_rating", "amenity"]

    def filter_amenity(self, queryset, name, value):
        # JSONField list-containment (`contains=[value]`) isn't portable across
        # backends (unsupported on SQLite, used in tests) — filter in Python.
        # Fine at directory scale (hundreds, not millions, of hostels).
        matching_ids = [
            hostel.pk for hostel in queryset.select_related("discovery_profile")
            if value in (hostel.discovery_profile.amenity_tags or [])
        ]
        return queryset.filter(pk__in=matching_ids)
