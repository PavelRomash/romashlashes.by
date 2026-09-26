from django.contrib import admin

from .models import FAQ, PortfolioItem, Service, SiteSettings


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price_from",
        "price_to",
        "currency",
        "is_active",
        "sort_order",
    )

    list_editable = (
        "is_active",
        "sort_order",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    search_fields = (
        "name",
        "short_description",
        "description",
    )


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "is_active",
        "sort_order",
    )

    list_editable = (
        "is_active",
        "sort_order",
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = (
        "question",
        "service",
        "is_active",
        "sort_order",
    )

    list_editable = (
        "is_active",
        "sort_order",
    )

    list_filter = (
        "service",
        "is_active",
    )


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    pass