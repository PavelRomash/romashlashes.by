from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from .models import Service, SiteSettings


def home(request):
    services = Service.objects.filter(is_active=True)
    site_settings = SiteSettings.objects.first()

    context = {
        "services": services,
        "site_settings": site_settings,
    }

    return render(request, "website/home.html", context)


def service_detail(request, slug):
    service = get_object_or_404(
        Service,
        slug=slug,
        is_active=True,
    )

    related_services = (
        Service.objects.filter(is_active=True)
        .exclude(pk=service.pk)
        .order_by("sort_order", "name")[:3]
    )

    site_settings = SiteSettings.objects.first()

    context = {
        "service": service,
        "related_services": related_services,
        "site_settings": site_settings,
    }

    return render(request, "website/service_detail.html", context)

def privacy(request):
    site_settings = SiteSettings.objects.first()

    return render(
        request,
        "website/privacy.html",
        {"site_settings": site_settings},
    )


def custom_404(request, exception=None):
    services = Service.objects.filter(is_active=True).order_by(
        "sort_order",
        "name",
    )[:4]

    return render(
        request,
        "404.html",
        {"services": services},
        status=404,
    )

def robots_txt(request):
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            "Sitemap: https://romashlashes.by/sitemap.xml",
        ]
    )

    return HttpResponse(
        content,
        content_type="text/plain",
    )