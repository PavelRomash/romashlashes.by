# Migration from static site to Django

## Goal

Migrate the existing `romashlashes.by` static HTML/CSS/JavaScript website to Django while preserving the existing visual design and SEO structure.

The new application should allow editable content such as services, prices, FAQ and contact information to be managed through Django Admin.

## Application stack

The application stack currently consists of:

~~~text
Python
Django
PostgreSQL
HTML
CSS
Vanilla JavaScript
~~~

The planned production stack is:

~~~text
Nginx
  ↓
Gunicorn
  ↓
Django
  ↓
PostgreSQL
~~~

No frontend framework such as React or Vue is used.

## Project structure

~~~text
romashlashes.by/
├── app/
│   ├── config/
│   ├── website/
│   ├── templates/
│   ├── static/
│   ├── manage.py
│   ├── requirements.txt
│   └── docker-compose.yml
│
├── ansible/
├── packer/
├── terraform/
├── kubernetes/
├── helm/
├── argocd/
├── monitoring/
├── logging/
└── docs/
~~~

## Local development environment

Django currently runs directly from a Python virtual environment on the Mac.

PostgreSQL runs locally in Docker.

~~~text
Mac
├── Django (.venv)
│   └── 127.0.0.1:8000
│
└── Docker
    └── PostgreSQL
        └── localhost:5432
~~~

PostgreSQL is started with:

~~~bash
docker compose up -d
~~~

The Django development server is started with:

~~~bash
python manage.py runserver
~~~

## Environment variables

Application configuration is stored in:

~~~text
app/.env
~~~

The file contains values such as:

~~~text
DJANGO_SECRET_KEY
DJANGO_DEBUG

POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
~~~

The `.env` file is excluded from Git.

Django loads it using `python-dotenv`.

## PostgreSQL

Django uses PostgreSQL instead of SQLite.

Database configuration is loaded from environment variables.

Local PostgreSQL runs using Docker Compose.

A persistent Docker volume is used for database data.

## Django models

The `website` application currently contains the following models.

### Service

Stores service information:

~~~text
name
slug
short_description
description
price_from
price_to
currency
seo_title
seo_description
is_active
sort_order
~~~

### FAQ

Stores questions and answers associated with services.

~~~text
service
question
answer
sort_order
is_active
~~~

### PortfolioItem

Stores portfolio images and videos.

~~~text
title
image
video
sort_order
is_active
~~~

### SiteSettings

Stores global website information.

~~~text
master_name
phone
address
instagram_url
telegram_username
viber_phone
dikidi_url
~~~

## Django Admin

Django Admin is used to manage website content.

The standard `/admin/` URL was replaced with a custom URL.

The admin interface currently allows management of:

~~~text
Services
FAQ
Portfolio
Site settings
~~~

## Legacy site import

The original website consisted of static HTML files.

Instead of manually recreating all content in Django Admin, a Django management command was created:

~~~text
website/management/commands/import_legacy_site.py
~~~

The command imports content from the legacy HTML website into PostgreSQL.

Example:

~~~bash
python manage.py import_legacy_site ../legacy-site/romashlashes.by
~~~

The importer extracts:

~~~text
service names
slugs
prices
SEO titles
SEO descriptions
descriptions
FAQ
~~~

The importer uses Django ORM `update_or_create()` so it can be safely executed multiple times without creating duplicate services.

## Templates

The website uses Django templates.

Current structure:

~~~text
templates/
├── base.html
├── 404.html
└── website/
    ├── home.html
    ├── service_detail.html
    └── privacy.html
~~~

### base.html

Contains common page structure:

~~~text
HTML document
<head>
CSS
header
main block
JavaScript
~~~

Other templates extend it using:

~~~django
{% extends "base.html" %}
~~~

## Home page

The old static `index.html` was converted into:

~~~text
templates/website/home.html
~~~

Services displayed on the page now come from PostgreSQL.

Example flow:

~~~text
PostgreSQL
    ↓
Service model
    ↓
Django view
    ↓
home.html
~~~

## Service pages

The old website had separate HTML files for each service.

Examples:

~~~text
narashchivanie-resnits-vitebsk.html
laminirovanie-resnits-vitebsk.html
korrektsiya-brovei-vitebsk.html
laminirovanie-brovei-vitebsk.html
~~~

The Django version uses one reusable template:

~~~text
templates/website/service_detail.html
~~~

Services are resolved using their slug.

Example:

~~~text
/narashchivanie-resnits-vitebsk/
/laminirovanie-resnits-vitebsk/
~~~

The flow is:

~~~text
URL slug
   ↓
Service model
   ↓
service_detail view
   ↓
service_detail.html
~~~

One template therefore serves all service pages.

## FAQ

FAQ content is stored in PostgreSQL and associated with a service through a ForeignKey.

The service template renders active FAQ dynamically.

This removes duplicated FAQ HTML from individual service pages.

## Static files

Static files were migrated to:

~~~text
app/static/
├── css/
│   └── styles.css
├── js/
│   └── app.js
└── assets/
    ├── images
    ├── video
    ├── SVG
    └── favicon files
~~~

Django static files are referenced using:

~~~django
{% load static %}
~~~

Example:

~~~django
{% static 'assets/hero.webp' %}
~~~

## Privacy page

The old static privacy page was migrated to:

~~~text
templates/website/privacy.html
~~~

and is available at:

~~~text
/privacy/
~~~

## Custom 404

A custom Django 404 handler was added.

~~~text
templates/404.html
~~~

The handler:

~~~text
website.views.custom_404
~~~

is configured using:

~~~python
handler404 = "website.views.custom_404"
~~~

Custom 404 rendering is used when Django runs with:

~~~text
DEBUG=False
~~~

## robots.txt

`robots.txt` is generated through a Django view.

Current production value:

~~~text
User-agent: *
Allow: /

Sitemap: https://romashlashes.by/sitemap.xml
~~~

## Sitemap

Django Sitemap Framework is enabled.

The sitemap includes:

~~~text
home page
active service pages
~~~

Service URLs are generated directly from active `Service` records in PostgreSQL.

Adding a new active service through Django Admin therefore automatically adds it to the sitemap.

## Current status

The static website has been migrated to Django.

Completed:

~~~text
[x] Django project
[x] PostgreSQL
[x] Django Admin
[x] Service model
[x] FAQ model
[x] SiteSettings model
[x] Portfolio model
[x] legacy HTML importer
[x] home page
[x] dynamic service pages
[x] privacy page
[x] custom 404
[x] static CSS/JS/assets
[x] robots.txt
[x] dynamic sitemap.xml
~~~

## Remaining work

Before production deployment:

~~~text
[ ] Add 301 redirects from legacy *.html URLs
[ ] Remove remaining hardcoded contact links from JavaScript/templates
[ ] Verify SEO metadata
[ ] Verify OpenGraph metadata
[ ] Verify JSON-LD structured data
[ ] Test custom 404 with DEBUG=False
[ ] Create production Dockerfile
[ ] Configure Gunicorn
[ ] Configure Nginx
[ ] Configure production Django settings
[ ] Deploy to DEV
[ ] Promote to STAGE
[ ] Promote to PROD
~~~