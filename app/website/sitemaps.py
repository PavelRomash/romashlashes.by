from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Service


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "weekly"

    def items(self):
        return ["home"]

    def location(self, item):
        return reverse(item)


class ServiceSitemap(Sitemap):
    priority = 0.9
    changefreq = "monthly"

    def items(self):
        return Service.objects.filter(
            is_active=True
        ).order_by(
            "sort_order",
            "name",
        )

    def location(self, service):
        return reverse(
            "service_detail",
            kwargs={
                "slug": service.slug,
            },
        )


sitemaps = {
    "static": StaticViewSitemap,
    "services": ServiceSitemap,
}