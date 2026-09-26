from django.urls import path

from . import views


urlpatterns = [
    path("", views.home, name="home"),

    path("privacy/", views.privacy, name="privacy"),

    path(
        "<slug:slug>/",
        views.service_detail,
        name="service_detail",
    ),

]