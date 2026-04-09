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

### Scouting / Prospective Products (`/scouting/`)
Tool for tracking products spotted at trade shows. Alex uses this to photograph and log potential new items from vendor booths. Each prospect has vendor info, unit cost, lead time, notes, and a photo. When a prospect gets approved it can be promoted to a full Product.

**This is the preferred workflow for adding new products:**
1. Add a prospect via the scouting tool (photo uploads work automatically)
2. Review and evaluate
3. Promote to a full Product record when ready

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
- Git HEAD.lock cannot be deleted from the sandbox (FUSE mount restriction) — run `rm -f .git/HEAD.lock .git/index.lock` locally before pushing if lock errors appear
