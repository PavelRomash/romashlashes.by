from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from website.sitemaps import sitemaps
from website.views import robots_txt


urlpatterns = [
    path(
        "robots.txt",
        robots_txt,
        name="robots_txt",
    ),

    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),

    path(
        "control-panel-7f3a/",
        admin.site.urls,
    ),

    path(
        "",
        include("website.urls"),
    ),
]


handler404 = "website.views.custom_404"