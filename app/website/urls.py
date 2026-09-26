from django.urls import path
from django.views.generic import RedirectView

from . import views


urlpatterns = [
    path(
        "",
        views.home,
        name="home",
    ),

    path(
        "privacy/",
        views.privacy,
        name="privacy",
    ),

    # Legacy URLs from the old static website.
    path(
        "narashchivanie-resnits-vitebsk.html",
        RedirectView.as_view(
            pattern_name="service_detail",
            permanent=True,
        ),
        {
            "slug": "narashchivanie-resnits-vitebsk",
        },
    ),

    path(
        "laminirovanie-resnits-vitebsk.html",
        RedirectView.as_view(
            pattern_name="service_detail",
            permanent=True,
        ),
        {
            "slug": "laminirovanie-resnits-vitebsk",
        },
    ),

    path(
        "korrektsiya-brovei-vitebsk.html",
        RedirectView.as_view(
            pattern_name="service_detail",
            permanent=True,
        ),
        {
            "slug": "korrektsiya-brovei-vitebsk",
        },
    ),

    path(
        "laminirovanie-brovei-vitebsk.html",
        RedirectView.as_view(
            pattern_name="service_detail",
            permanent=True,
        ),
        {
            "slug": "laminirovanie-brovei-vitebsk",
        },
    ),

    path(
        "privacy.html",
        RedirectView.as_view(
            pattern_name="privacy",
            permanent=True,
        ),
    ),

    # Keep dynamic service URL last.
    path(
        "<slug:slug>/",
        views.service_detail,
        name="service_detail",
    ),
]