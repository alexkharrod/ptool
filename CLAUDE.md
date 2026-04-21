# ptool — LogoIncluded Internal Product Tool

Built and maintained by Alex (President, LogoIncluded) with Claude.
This is an internal Django web app for managing promotional products, quotes, and scouting new items.

---

## What this tool does

### Products (`/products/`)
Full product catalog for LogoIncluded's line. Each product has SKU, specs, carton info, imprint details, freight/tariff costs, and an image. From a product page you can download a **NPDS (New Product Data Sheet)** as a PDF.

### Quotes (`/quotes/`)
Customer quote builder. Fully redesigned (April 2026). Key features:
- **SalesRep model** (separate from Django users) — name + initials, used in quote numbers and PDFs
- **Quote number format**: `MMDD-REP-SKU-NN` (e.g. `0409-PM-AT01-01`) — assigned when first item is added; shows "Draft" until then
- **Pricing tiers**: default 1, up to 5 per item; empty tiers are not saved
- **Internal fields** (never printed): Unit Cost, Our Air Freight, Our Ocean Freight
- **Customer-facing fields**: Air Total, Ocean Total, Air Production Time, Ocean Production Time
- **Auto-save**: Preview and PDF buttons save all unsaved item data before navigating
- **PDF**: no cover page; one item per page; logo + contact info in header; disclaimer and rep thank-you on last page
- **Quote-only products**: products without website URLs work fine in quotes

### Shipments (`/shipments/`)
Inbound shipment tracker for air and ocean freight (added April 2026). Key features:
- **Shipment** model: sequential `shipment_number`, AGS#, mode (Air/Ocean), carrier, vessel, tracking#/AWB, ETD, ETA port, ETA warehouse (+12 days auto-fill from ETA port), port of arrival, status, totals (cartons, pieces, CBM, NW kg, GW kg), notes
- **ShipmentItem** model: per-line-item from packing list — PO#, SKU, description, cartons, qty, NW/GW (kg), CBM, dimensions, `unit_cost_usd` (internal, logistics-only)
- **ShipmentDocument** model: file attachments (packing list, invoice, BOL, etc.) stored via Cloudinary
- **Status choices**: Ordered → In Transit → Arrived Port → In Customs → Out for Delivery → Delivered / Cancelled
- **Two-tier access control** (see Users section below):
  - `access_shipments` — view list and detail, no costs shown
  - `access_shipments_logistics` — full access: add/edit shipments, see unit costs
  - Staff always have full access
- **Quick status update**: inline dropdown on list view posts to `/shipments/<pk>/update-status/` via AJAX
- **XLS/XLSX auto-parse**: upload a packing list or commercial invoice on the add/edit page; `parse_doc.py` extracts all line items and cross-references unit costs from CI
- Default list view excludes Delivered/Cancelled; checkbox shows all
- Search works across AGS#, PO#, SKU, carrier

Key files:
| File | Purpose |
|------|---------|
| `shipments/models.py` | Shipment, ShipmentItem, ShipmentDocument |
| `shipments/views.py` | list, detail, add, edit, upload_doc, delete_doc, update_status, parse_doc |
| `shipments/forms.py` | ShipmentForm, ShipmentItemForm, ShipmentDocumentForm |
| `shipments/parse_doc.py` | XLS/XLSX parser — detects PL/CI sheets, extracts items + costs |
| `shipments/templates/shipments/` | shipment_list, shipment_detail, shipment_add, shipment_edit |
| `shipments/migrations/0001_initial.py` | Creates Shipment, ShipmentItem, ShipmentDocument tables |
| `shipments/migrations/0002_shipment_nw_and_item_cost.py` | Adds total_nw_kg to Shipment, unit_cost_usd to ShipmentItem |
| `shipments/management/commands/create_shipment_120.py` | One-time command to seed shipment #120 (Bluefin/ZIM ocean shipment) |

### Scouting / Prospective Products (`/scouting/`)
Tool for tracking products spotted at trade shows. Alex uses this to photograph and log potential new items from vendor booths. Each prospect has vendor info, unit cost, lead time, notes, and a photo. When a prospect gets approved it can be promoted to a full Product.

**This is the preferred workflow for adding new products:**
1. Add a prospect via the scouting tool (photo uploads work automatically)
2. Review and evaluate
3. Promote to a full Product record when ready

---

## Users & Permissions

All access is controlled via `BooleanField` flags on `CustomUser`. Staff (`is_staff=True`) bypass all flags and always have full access.

| Field | Grants access to |
|-------|-----------------|
| `access_products` | Products section |
| `access_quotes` | Quotes section |
| `access_scouting` | Scouting section |
| `access_shipments` | Shipments — view only, no unit costs |
| `access_shipments_logistics` | Shipments — add/edit, see unit costs |

**Convenience properties on CustomUser** (use these in views/templates):
- `can_access_products`, `can_access_quotes`, `can_access_scouting`
- `can_access_shipments` — True if staff OR access_shipments OR access_shipments_logistics
- `can_access_shipments_logistics` — True if staff OR access_shipments_logistics

**Shipment view helpers:**
```python
def _can_access(user):   # view list/detail
    return user.is_staff or user.access_shipments or user.access_shipments_logistics

def _can_edit(user):     # add/edit + unit costs
    return user.is_staff or user.access_shipments_logistics
```

**User management**: Admin → Users; instant-toggle checkboxes on the manage page; edit page has full access controls. Creating users: `create_user()` only accepts `email`, `password`, `first_name`, `last_name`, `must_change_password` — all other access flags must be set via a subsequent `save()` call.

Migrations:
| Migration | Purpose |
|-----------|---------|
| `users/migrations/0004_add_access_shipments.py` | Adds `access_shipments` |
| `users/migrations/0005_add_access_shipments_logistics.py` | Adds `access_shipments_logistics` |

---

## Deployment

- **Production**: Railway.app — auto-deploys on push to `main`
- **Database**: Railway PostgreSQL (shared between local dev and production)
- **Image storage**: Cloudinary — all product and quote images upload there automatically via `ImageField`
- **Static files**: served via `whitenoise` from `staticfiles/`
- **PDF generation**: WeasyPrint (lazy-imported to avoid startup crashes)

### Local development
Requires a `.env` file in the project root (never committed — in `.gitignore`):
```
SECRET_KEY=...
DEBUG=True
DATABASE_URL="postgresql://postgres:PASSWORD@interchange.proxy.rlwy.net:PORT/railway"
CLOUDINARY_URL="cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
```
With `DATABASE_URL` set, local and Railway share the same Postgres database — changes made locally appear on Railway immediately.

---

## Image storage

Products and quotes use `ImageField` (upload_to `products/` and `quotes/` respectively). Images are:
- Automatically compressed and resized to max 800px wide on upload (via `compress_image()` in each model's `save()`)
- Stored on Cloudinary in production
- Old `image_url` CharField kept on both models as a fallback for any records not yet migrated

### Bulk upload legacy images
If you ever need to re-run the legacy image migration (static/images → Cloudinary):
```bash
DATABASE_URL="..." CLOUDINARY_URL="..." python manage.py upload_product_images
# Add --dry-run to preview, --sku EB59 LY1302 to target specific SKUs
```

---

## Key files

| File | Purpose |
|------|---------|
| `mysite/settings.py` | Main settings — DB, Cloudinary, static files all configured here |
| `products/models.py` | Product model with compress_image and ImageField |
| `quotes/models.py` | `SalesRep`, `CustomerQuote`, `QuoteLineItem` models; `_next_quote_number()` generates MMDD-REP-SKU-NN |
| `scouting/models.py` | Prospect model — the reference implementation for image upload pattern |
| `users/models.py` | `CustomUser` with all access flags and convenience properties |
| `users/views.py` | user_manage, user_create, user_edit, user_toggle_access (AJAX) |
| `products/views.py` | Includes `npds()` — PDF datasheet download (logo embedded as base64) |
| `quotes/views.py` | Includes `cq_pdf()`, `cq_view()`, `cq_item_add()`, `cq_item_save()`, `cq_rep_add()` |
| `quotes/templates/cq/cq_edit.html` | Quote edit page — item cards, pricing tiers, auto-save before navigate |
| `quotes/templates/cq/_item_card.html` | Individual item card partial |
| `quotes/templates/cq/cq_pdf.html` | Quote PDF template — WeasyPrint, base64 logo, disclaimer, thank-you |
| `quotes/templates/cq/cq_view.html` | Quote preview page |
| `quotes/migrations/` | 0021: SalesRep model + drop User FK; 0022: quote improvements; 0023: initials field + seed reps |
| `products/management/commands/upload_product_images.py` | One-time bulk upload of legacy static images to Cloudinary |
| `static/images/LI-Circle.png` | LogoIncluded logo — loaded as base64 in NPDS and quote PDFs |
| `Dockerfile` | Railway build — Debian Bookworm base for WeasyPrint system libs |
| `shipments/models.py` | Shipment, ShipmentItem, ShipmentDocument |
| `shipments/views.py` | list, detail, add, edit, upload_doc, delete_doc, update_status, parse_doc |
| `shipments/parse_doc.py` | XLS/XLSX packing list / commercial invoice parser |

---

## Sales Reps

Seeded in migration 0023. Current reps:
| Initials | Name |
|----------|------|
| AH | Alex Harrod |
| KA | Kenny Avera |
| PM | Peter Marks |
| JW | Jake Wilson |
| JG | Joey Guerrero |
| SW | Sari Waters |

`initials` field is `null=True, unique=True` — multiple NULLs allowed in Postgres unique index (safe for reps without initials set).

---

## Known issues / backlog
- 3 products still have no image (find them by browsing products list — no image shown)
- `newsku` and `newskuaa` are test/placeholder SKUs that can be deleted
- Git HEAD.lock / index.lock cannot be deleted from the sandbox (FUSE mount restriction) — run `rm -f .git/HEAD.lock .git/index.lock` locally before pushing if lock errors appear. Useful alias: `git config --global alias.unlock '!rm -f .git/HEAD.lock .git/index.lock'`
