import re
from decimal import Decimal
from pathlib import Path

from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from website.models import FAQ, Service


SERVICES = {
    "narashchivanie-resnits-vitebsk.html": {
        "name": "Наращивание ресниц",
        "sort_order": 10,
    },
    "laminirovanie-resnits-vitebsk.html": {
        "name": "Ламинирование ресниц",
        "sort_order": 20,
    },
    "korrektsiya-brovei-vitebsk.html": {
        "name": "Коррекция и окрашивание бровей",
        "sort_order": 30,
    },
    "laminirovanie-brovei-vitebsk.html": {
        "name": "Ламинирование бровей",
        "sort_order": 40,
    },
}


class Command(BaseCommand):
    help = "Import services and FAQ from the old static romashlashes.by site"

    def add_arguments(self, parser):
        parser.add_argument(
            "site_path",
            type=str,
            help="Path to the old static site directory",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        site_path = Path(options["site_path"]).resolve()

        if not site_path.exists():
            raise CommandError(f"Directory does not exist: {site_path}")

        self.stdout.write(
            self.style.NOTICE(f"Importing legacy site from: {site_path}")
        )

        imported_services = 0
        imported_faqs = 0

        for filename, config in SERVICES.items():
            html_path = site_path / filename

            if not html_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"Skipping missing file: {filename}")
                )
                continue

            service, faq_count = self.import_service(
                html_path=html_path,
                name=config["name"],
                sort_order=config["sort_order"],
            )

            imported_services += 1
            imported_faqs += faq_count

            self.stdout.write(
                self.style.SUCCESS(
                    f"Imported: {service.name} ({faq_count} FAQ)"
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Services: {imported_services}, FAQ: {imported_faqs}"
            )
        )

    def import_service(self, html_path, name, sort_order):
        html = html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")

        slug = html_path.stem

        seo_title = self.get_title(soup)
        seo_description = self.get_meta_description(soup)

        short_description = self.get_short_description(soup)
        description = self.get_description(soup)

        price_from, price_to, currency = self.get_price(soup)

        service, created = Service.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "short_description": short_description,
                "description": description,
                "price_from": price_from,
                "price_to": price_to,
                "currency": currency,
                "seo_title": seo_title,
                "seo_description": seo_description,
                "is_active": True,
                "sort_order": sort_order,
            },
        )

        if created:
            self.stdout.write(f"  Created service: {name}")
        else:
            self.stdout.write(f"  Updated service: {name}")

        faq_count = self.import_faqs(service, soup)

        return service, faq_count

    def get_title(self, soup):
        if soup.title:
            return soup.title.get_text(" ", strip=True)

        return ""

    def get_meta_description(self, soup):
        tag = soup.find("meta", attrs={"name": "description"})

        if tag:
            return tag.get("content", "").strip()

        return ""

    def get_short_description(self, soup):
        hero = soup.select_one(".service-detail-copy")

        if not hero:
            return ""

        paragraph = hero.find("p")

        if not paragraph:
            return ""

        return paragraph.get_text(" ", strip=True)

    def get_description(self, soup):
        section = soup.select_one(".services-section .seo-copy")

        if not section:
            return ""

        paragraphs = [
            paragraph.get_text(" ", strip=True)
            for paragraph in section.find_all("p", recursive=False)
        ]

        return "\n\n".join(paragraphs)

    def get_price(self, soup):
        price_element = None

        for element in soup.select(".service-fact"):
            text = element.get_text(" ", strip=True)

            if text.startswith("Цена:"):
                price_element = text
                break

        if not price_element:
            return None, None, "BYN"

        price_text = price_element.replace("Цена:", "").strip()

        currency_match = re.search(r"\b([A-Z]{3})\b", price_text)
        currency = currency_match.group(1) if currency_match else "BYN"

        numbers = re.findall(r"\d+(?:[.,]\d+)?", price_text)

        if not numbers:
            return None, None, currency

        values = [
            Decimal(number.replace(",", "."))
            for number in numbers
        ]

        price_from = values[0]
        price_to = values[1] if len(values) > 1 else None

        return price_from, price_to, currency

    def import_faqs(self, service, soup):
        faq_items = soup.select("#faq details")

        imported_questions = []

        for sort_order, item in enumerate(
            faq_items,
            start=1,
        ):
            summary = item.find("summary")
            answer = item.find("p")

            if not summary or not answer:
                continue

            question = summary.get_text(" ", strip=True)
            answer_text = answer.get_text(" ", strip=True)

            FAQ.objects.update_or_create(
                service=service,
                question=question,
                defaults={
                    "answer": answer_text,
                    "sort_order": sort_order * 10,
                    "is_active": True,
                },
            )

            imported_questions.append(question)

        FAQ.objects.filter(
            service=service,
        ).exclude(
            question__in=imported_questions,
        ).delete()

        return len(imported_questions)