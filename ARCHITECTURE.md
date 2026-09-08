# ptool — Architecture & Working Overview

An orientation document for someone (or some model) picking this project up cold.
Describes what the system does and how it is built, as of September 2026.

---

## 1. What this is

**ptool** is an internal Django web application for **LogoIncluded**, a promotional
products company. It is used by the company's president and a small number of sales
and logistics staff — on the order of ten users, not a public-facing product.

It covers four areas of the business:

| Module | Path | Purpose |
|---|---|---|
| **Products** | `/products/` | The master catalog: specs, costs, tariffs, imprint options, website copy |
| **Quotes** | `/quotes/` | Customer-facing quote builder with tiered pricing, exports to PDF |
| **Shipments** | `/shipments/` | Inbound freight tracker for air and ocean shipments from Chinese suppliers |
| **Scouting** | `/scouting/` | Logging prospective new products spotted at trade shows |

The through-line: a product is **spotted** at a trade show (Scouting), **added** to the
catalog with full specs and landed-cost data (Products), **quoted** to a customer
(Quotes), and the resulting order is **tracked** inbound from the factory (Shipments).
Those four modules mirror that lifecycle, though they are only loosely coupled in
the data model — see §5.

---

## 2. Stack and deployment

- **Django 4.2** (Python 3.12), server-rendered templates — no SPA, no REST API
- **Bootstrap 5** + Bootstrap Icons, `django-widget-tweaks` for form field classes
- Interactivity is **vanilla JS inline in templates** (`fetch()` to small JSON
  endpoints). No build step, no npm, no framework
- **PostgreSQL** on Railway; falls back to local SQLite (`instance/db.sqlite3`) if
  `DATABASE_URL` is unset
- **Railway.app** hosting, auto-deploys on push to `main`. `Dockerfile` uses a Debian
  Bookworm base to supply WeasyPrint's system libraries
- **WhiteNoise** serves static files from `staticfiles/`
- **Cloudinary** stores uploaded images and documents; enabled by presence of
  `CLOUDINARY_URL`, otherwise media goes to the local `media/` directory
- **WeasyPrint** renders PDFs (imported lazily inside views, to keep a missing
  system library from crashing startup)
- **Anthropic API** powers several AI features (§6)

### Environment variables

| Var | Purpose |
|---|---|
| `SECRET_KEY` | Required — settings raises `ValueError` if absent |
| `DATABASE_URL` | Postgres connection string, parsed by `dj_database_url` |
| `CLOUDINARY_URL` | Enables Cloudinary storage when set |
| `ANTHROPIC_API_KEY` | Claude API access for AI features |
| `DEBUG` | Defaults to `False` |
| `ALLOWED_HOSTS` | Comma-separated; `CSRF_TRUSTED_ORIGINS` is derived from it |

Local development uses a `.env` file (gitignored). Because `DATABASE_URL` normally
points at Railway, **local development and production share one database** — there is
no separate staging DB. Changes made from a local shell are live immediately.

A nightly-ish `backup_db.sh` runs via launchd on the president's Mac at 9am and 3pm,
dumping Postgres to Dropbox with a size check and 30-day retention.

---

## 3. Users, auth and permissions

`AUTH_USER_MODEL` is `users.CustomUser` — email as username, no separate username
field. Django's group/permission system is **not** used for app authorization.

Access is instead a set of boolean flags on the user record:

| Flag | Grants |
|---|---|
| `access_products` | Products section |
| `access_quotes` | Quotes section |
| `access_scouting` | Scouting section |
| `access_shipments` | Shipments — view only, unit costs hidden |
| `access_shipments_logistics` | Shipments — add/edit, unit costs visible |

`is_staff=True` bypasses all flags. Convenience properties on `CustomUser`
(`can_access_products`, `can_access_shipments_logistics`, …) are what views and
templates should read, rather than the raw fields.

Enforcement is a single decorator, `@section_required("<section>")` in
`users/decorators.py`, applied to every view in the four section apps. It wraps
`login_required`, redirects users without the flag home (JSON 403 for fetch() calls),
and lets staff through. Sections are `products`, `quotes`, `scouting`, `shipments`
(view), `shipments_logistics` (add/edit + unit costs) and `staff` (vendor/HTS/category
management, reports). `users/tests.py` walks every URL under the section prefixes and
fails if a view lacks the decorator. `mysite/middleware.py::PtoolAccessMiddleware`
now only forces the password change when `must_change_password` is set and keeps
non-staff out of `/admin/`.

`django-axes` provides brute-force protection: 5 failures locks the
(username, IP) pair for 1 hour. Minimum password length is 12.

Legacy fields `role` and `scouting_only` remain on `CustomUser`; the `access_*`
flags supersede them.

User administration lives at `/users/manage/`, with instant-toggle AJAX checkboxes.
Note that `CustomUserManager.create_user()` accepts only `email`, `password`,
`first_name`, `last_name`, `must_change_password` — any access flag must be set in a
follow-up `save()`.

---

## 4. The modules

### Products (`/products/`) — the largest module

The catalog of everything LogoIncluded sells. A `Product` carries roughly 45 fields
spanning several concerns:

- **Identity**: SKU (unique, generated per-category via `/products/next-sku/`), name,
  category, image
- **Physical**: carton quantity / weight / dimensions, colors, packaging, MOQ
- **Imprint**: location, dimension, mold fee, plus an M2M to `ImprintMethod`
- **Landed cost**: air and ocean freight, `hts_code` FK, duty %, tariff %
- **Web content**: `website_url`, `website_description`, `website_keywords`
- **Workflow flags**: `price_list`, `product_list`, `hts_list`, `npds_done`,
  `qb_added`, `published` — booleans tracking how far a product has progressed
  through the internal launch checklist, toggled inline from the list view

Supporting models: `Category` (code + SKU seed), `Vendor`, `ImprintMethod`, and
`HtsCode` (customs classification with duty, Section 301 and extra tariff
percentages, M2M to categories).

Notable views: `npds()` generates a **New Product Data Sheet** PDF; `bulk_update_products()`
applies field edits across many rows from the list view; `report_show_roi()` and
`report_published()` back a small reports section.

The module also owns 17 management commands — the largest cluster of automation in
the project (§7).

### Quotes (`/quotes/`)

Two quote systems currently coexist in this app.

**Current system** (redesigned April 2026), URLs under `/quotes/cq/`:

- `CustomerQuote` → `QuoteLineItem` → `QuotePriceTier`, a properly normalized
  three-level structure. Up to 5 price tiers per line item; empty tiers aren't saved
- `SalesRep` is its own model (deliberately separate from `CustomUser` — reps don't
  all have logins), carrying a name and initials
- **Quote numbers** follow `MMDD-REP-SKU-NN` (e.g. `0409-PM-AT01-01`), assigned when
  the first line item is added; a quote shows as "Draft" until then
- **Internal vs customer-facing fields** is the key distinction: Unit Cost, Our Air
  Freight and Our Ocean Freight never appear on the PDF. Air Total, Ocean Total and
  the production times do
- The edit page auto-saves unsaved item data before navigating to Preview or PDF
- PDF: no cover page, one item per page, logo and contact block in the header,
  disclaimer and rep thank-you on the final page

**Legacy system**, URLs under `/quotes/quotes/`, `/quotes/create-quote/` etc.:
the original flat `Quote` model, which stores pricing as 15 repeated columns
(`quantity1`–`quantity5`, `qty1_cost`…`qty5_price_ocean`) rather than tier rows.
Its views, templates and URLs are all still wired up and reachable.

### Shipments (`/shipments/`)

Added April 2026, most recently modified September 2026. Tracks inbound freight.

- `Shipment` — sequential number, AGS# (freight forwarder ref), mode (Air/Ocean),
  carrier, vessel, tracking#/AWB, ETD, ETA port, ETA warehouse, port of arrival,
  status, and totals (cartons, pieces, CBM, NW kg, GW kg)
- `ShipmentItem` — one packing-list line: PO#, SKU, description, cartons, qty,
  NW/GW, CBM, dimensions, and `unit_cost_usd` (logistics-only)
- `ShipmentDocument` — attached packing lists, invoices, BOLs via Cloudinary

Status flow: Ordered → In Transit → Arrived Port → In Customs → Out for Delivery →
Delivered / Cancelled. The list view excludes Delivered and Cancelled by default
(a checkbox reveals them), and offers an inline status dropdown that POSTs to
`/shipments/<pk>/update-status/`.

**Packing list import** is the module's most involved piece. `shipments/parse_doc.py`
accepts an uploaded `.xls`/`.xlsx`, classifies its sheets as packing list and/or
commercial invoice, and extracts line items plus totals, cross-referencing unit costs
from the CI when present. The parser handles the two-row merged header layout these
supplier spreadsheets use — it forward-fills merged group titles across blank cells and
joins them with the sub-header row, so a column reads as `"n.w. (kgs) total"` versus
`"n.w. (kgs) n.w/ctn"`. That distinction is what lets it pick per-line totals rather
than per-carton values. Suppliers label that sub-column either `SUB` or `Total`
depending on the workbook, and both are handled. Decimal precision is quantized
per-field to match the model columns (weights 2 dp, CBM 4 dp).

The add/edit form reorders itself by mode: selecting **Air** hides the ocean-only
fields (AGS#, vessel, ports, ETA port, CBM), leaving carrier, tracking #, PO numbers
and ship date. Hidden fields stay in the DOM so values survive a mode switch.

### Scouting (`/scouting/`)

A trade-show capture tool, and the intended front door for new products.

A `Prospect` holds vendor contact details, product name, unit cost, lead time, colors,
notes and a photo, with a `PRO-NNNN` reference number and a status
(Spotted → Sample Ordered → Evaluating → Adding → Rejected). There's an active-show
concept (`/scouting/set-show/`) so successive entries inherit the show name, and a
business-card scanner (`/scouting/scan-card/`) that sends a photo to Claude to
extract vendor contact fields.

Promotion to a real product (`/scouting/<pk>/promote/`) sets `promoted=True` and
records `promoted_sku` as **text** — there is no ForeignKey from `Prospect` to
`Product`, so the link is by SKU string only.

Image handling here is the reference implementation: `compress_image()` applies EXIF
orientation (so phone photos aren't sideways), converts to RGB, resizes to 800px wide
and saves as JPEG before upload.

---

## 5. Data model relationships

```
users.CustomUser ──(no FK to anything; access via boolean flags)

products.Category ──M2M── products.HtsCode
products.Vendor ◄──FK── products.Product ──FK──► products.HtsCode
                                         ──FK──► products.Category
                                         ──M2M─► products.ImprintMethod

quotes.SalesRep ◄──FK── quotes.CustomerQuote
                              │
                              └─FK── quotes.QuoteLineItem ──FK──► products.Product
                                            │
                                            └─FK── quotes.QuotePriceTier

quotes.Quote (legacy) ──FK──► products.HtsCode, products.Vendor

shipments.Shipment ──FK── shipments.ShipmentItem     (SKU stored as text)
                   ──FK── shipments.ShipmentDocument

scouting.Prospect                                     (promoted_sku stored as text)
```

Two joins that a reader might expect to exist, but don't:

- `Prospect` → `Product` is a SKU string, not a relation
- `ShipmentItem.sku` is a plain CharField, not a FK to `Product` — so shipments and
  the catalog are joined by string matching, not referentially

`Product` also retains legacy text columns (`vendor`, `imprint_method`) alongside
their newer relational equivalents (`vendor_ref` FK, `imprint_methods` M2M).

---

## 6. AI features (Anthropic API)

The `anthropic` client is imported lazily inside each view that needs it.

| Feature | Location | Behavior |
|---|---|---|
| **HTS code suggestion** | `products/views.py::hts_ai_suggest`, `hts_ai_suggest_text` | Suggests a customs classification from a product record or free text |
| **Website description** | `products/views.py::generate_description` | Generates marketing copy. Deliberately excludes SKU, colors, MOQ, imprint info, packaging and production time; capped at 800 characters via prompt instruction and a 350-token limit rather than truncation |
| **SEO keywords** | `products/views.py::generate_keywords` | Generates a keyword list under a no-repeated-words constraint — enforced both in the prompt and by a post-processing dedup pass, so you get `microphone, lavalier, wireless` rather than `wireless microphone, lavalier microphone` |
| **Business card scan** | `scouting/views.py` | Extracts vendor contact fields from a photographed card. `DATA_UPLOAD_MAX_MEMORY_SIZE` is raised to 10MB for these base64 payloads |

---

## 7. Management commands

Twenty-four commands across the apps. Broadly three kinds:

**Ongoing utilities**
- `generate_web_content` — batch AI description/keyword fill for products missing them
- `import_from_sitemap` — Playwright-driven scrape of logoincluded.com to import
  product data (651 lines, the largest single file after `products/views.py`)
- `website_product_gap` — diffs the live sitemap against the DB, outputs an Excel gap report
- `export_hts_list`, `export_hts_spreadsheet`, `import_hts_spreadsheet` — Excel
  round-trip for bulk HTS/category data entry
- `upload_product_images` — bulk-uploads legacy static images to Cloudinary
  (supports `--dry-run` and `--sku` targeting)

**Seed commands** — `seed_categories`, `seed_hts_codes`, `seed_imprint_methods`, `seed_vendors`

**One-time data fixes and record seeds** — `fix_product_categories`, `fix_vendor_data`,
`fix_vendor_data_2`, `link_vendor_refs`, `stamp_website_urls`, `audit_bluetooth`,
`create_shipment_120`, `create_shipment_138`, `add_deeray_prospects`, `add_prospect`,
`import_prospect`, `create_claude_user`, `setup_users`

The seed-a-specific-record pattern (`create_shipment_138`, `add_deeray_prospects`)
exists because the sandbox used for development can't reach the Railway database —
so records are written as an idempotent command and run from the president's machine.

---

## 8. External data sources

- **logoincluded.com sitemap** — scraped via Playwright by `import_from_sitemap` and
  `website_product_gap`
- **Supplier spreadsheets** — parsed by `shipments/parse_doc.py` (openpyxl for `.xlsx`,
  xlrd for `.xls`)

`scrapy`, `parsel` and their transitive dependencies are present in
`requirements.txt` with no imports anywhere in the app code. (A hand-rolled
PromoStandards client was removed in September 2026 — nothing used it.)

---

## 9. Testing

```
DATABASE_URL="sqlite:///test.db" SECRET_KEY=test python manage.py test
```

`settings.py` sets `TESTING` when run via `manage.py test` and disables django-axes
(whose backend needs a request the test client doesn't supply) and the WhiteNoise
manifest storage. `mysite/settings_test.py` does the same for `--settings=mysite.settings_test`.

| File | Covers |
|---|---|
| `users/tests.py` | `section_required` decorator; a sweep of every URL under the section prefixes (anonymous → login, no-flag user → blocked, staff-only pages blocked for non-staff); middleware |
| `shipments/tests.py` | view-only vs logistics: what each can see, edit, and change; unit costs preserved on edit |
| `products/tests.py` | Vendor model + staff-only vendor views; access flags; bulk status update stamps `date_published` |
| `quotes/tests.py`, `scouting/` | No tests yet |

## 10. Repo map

```
mysite/          settings, root urls, PtoolAccessMiddleware
products/        catalog — models, 965-line views.py, 17 mgmt commands
quotes/          current (cq_*) + legacy quote systems, WeasyPrint PDF templates
shipments/       freight tracker, parse_doc.py spreadsheet parser
scouting/        trade-show prospects, business-card scan
users/           CustomUser, access flags, user administration
templates/       base.html and shared partials (219 .html files project-wide)
static/          images incl. LI-Circle.png (base64-embedded into PDFs)
Dockerfile       Railway build, Debian Bookworm for WeasyPrint libs
backup_db.sh     scheduled Postgres → Dropbox backup
CLAUDE.md        working notes and conventions for AI-assisted development
```

---

## 11. Current state notes

Things a reviewer should know are true right now, stated plainly:

- The **legacy `Quote` model and its views/URLs run in parallel** with the newer
  `CustomerQuote` system. Both are reachable.
- **`compress_image()` is defined three times** — in `products/models.py`,
  `quotes/models.py` and `scouting/models.py`. The products and scouting copies apply
  EXIF transposition; the quotes copy does not.
- **Local dev and production share one Postgres database.** There is no staging
  environment.
- **A few products have no image**, and `newsku`/`newskuaa` are placeholder SKUs left
  in the catalog.
- The repo contains a handful of loose scratch files at root (`build_manual.js`,
  `count_ps.py`, `hts_codes.xlsx`, `hts_list.xlsx`, `shipments_email_plan.md`) that
  aren't part of the application.
- `git` operations from the development sandbox hit FUSE lock issues; commits and
  pushes are run from the president's machine (`git config --global alias.unlock
  '!rm -f .git/HEAD.lock .git/index.lock'`).
