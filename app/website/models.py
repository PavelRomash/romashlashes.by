from django.db import models


class Service(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    short_description = models.TextField(blank=True)
    description = models.TextField(blank=True)

    price_from = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    price_to = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )

    currency = models.CharField(
        max_length=10,
        default="BYN",
    )

    seo_title = models.CharField(
        max_length=255,
        blank=True,
    )

    seo_description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class PortfolioItem(models.Model):
    title = models.CharField(
        max_length=200,
        blank=True,
    )

    image = models.ImageField(
        upload_to="portfolio/",
        blank=True,
        null=True,
    )

    video = models.FileField(
        upload_to="portfolio/videos/",
        blank=True,
        null=True,
    )

    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.title or f"Portfolio item {self.pk}"


class FAQ(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="faqs",
        null=True,
        blank=True,
    )

    question = models.CharField(max_length=255)
    answer = models.TextField()

    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.question


class SiteSettings(models.Model):
    master_name = models.CharField(
        max_length=200,
        blank=True,
    )

    phone = models.CharField(
        max_length=50,
        blank=True,
    )

    address = models.CharField(
        max_length=255,
        blank=True,
    )

    telegram_username = models.CharField(
        max_length=100,
        blank=True,
)

    viber_phone = models.CharField(
        max_length=50,
        blank=True,
)

    instagram_url = models.URLField(blank=True)
    dikidi_url = models.URLField(blank=True)

    def __str__(self):
        return "Site settings"

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"