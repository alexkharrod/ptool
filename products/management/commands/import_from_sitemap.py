"""
Management command: import_from_sitemap

Imports all active products from the logoincluded.com sitemap into ptool.
Scrapes full product data (MOQ, colors, carton, imprint, etc.) from each
product page using Playwright (headless Chromium).

Key SKU rules:
  - -US suffix is stripped from the canonical SKU (AT01-US → SKU AT01)
  - If both base (AT01) and -US (AT01-US) exist in the sitemap, the -US version
    wins: imported as SKU AT01, sourcing=domestic, needs_overseas_sku=True.
  - If only a base slug exists (no -US counterpart): imported as-is, sourcing=overseas.
  - RT-prefixed SKUs: sourcing=retail.
  - Existing SKUs are skipped.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python manage.py import_from_sitemap              # full import
    python manage.py import_from_sitemap --dry-run    # preview only
    python manage.py import_from_sitemap --limit 5    # first 5 products
    python manage.py import_from_sitemap --sku EC18 TT01  # specific SKUs
    python manage.py import_from_sitemap --skip-images    # don't upload to Cloudinary
    python manage.py import_from_sitemap --skip-generate  # don't call AI
    python manage.py import_from_sitemap --skip-scrape    # don't scrape product pages
"""

import ssl
import time
import urllib.request
from xml.etree import ElementTree

from django.core.management.base import BaseCommand

from products.models import Product

SITEMAP_URL = "https://www.logoincluded.com/sitemap-3.xml"
EWIZ_TENANT_ID = "B0CDADFD-F477-4E18-94A3-110C470D6097"

# SSL context for environments with self-signed proxy certs
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# Sitemap parsing
# ---------------------------------------------------------------------------

def fetch_sitemap_products():
    """
    Fetch and parse the sitemap.
    Returns a list of dicts:
        sku, name, product_url, image_url, sourcing, needs_overseas_sku
    """
    with urllib.request.urlopen(SITEMAP_URL, timeout=30, context=_SSL_CTX) as f:
        xml = f.read()

    root = ElementTree.fromstring(xml)
    SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
    IMAGE_NS   = "http://www.google.com/schemas/sitemap-image/1.1"

    # Iterate <url> elements and pair each product <loc> with its <image:loc>.
    # Structure: <url><loc>...</loc><image:image><image:loc>...</image:loc></image:image></url>
    # Use .//{ns}loc (descendant search) because image:loc is nested inside image:image.
    pairs = []
    for url_el in root.iter(f"{{{SITEMAP_NS}}}url"):
        loc_el = url_el.find(f"{{{SITEMAP_NS}}}loc")
        img_el = url_el.find(f".//{{{IMAGE_NS}}}loc")   # any descendant <image:loc>
        if loc_el is None:
            continue
        prod_url = loc_el.text.strip()
        if "logoincluded.com/product/" not in prod_url:
            continue
        img_url = img_el.text.strip() if img_el is not None else None
        pairs.append((prod_url, img_url))

    all_slugs = set()
    for prod_url, _ in pairs:
        slug = prod_url.rstrip("/").split("/")[-1].upper()
        all_slugs.add(slug)

    us_slugs = {s for s in all_slugs if s.endswith("-US")}
    base_slugs = all_slugs - us_slugs
    bases_with_us = {s for s in base_slugs if s + "-US" in us_slugs}

    products = []
    for prod_url, img_url in pairs:
        slug = prod_url.rstrip("/").split("/")[-1].upper()
        parts = prod_url.rstrip("/").split("/")
        name_slug = parts[-2] if len(parts) >= 2 else slug.lower()

        if slug in bases_with_us:
            continue  # the -US version will handle this

        canonical_sku = slug[:-3] if slug.endswith("-US") else slug

        if canonical_sku.startswith("RT"):
            sourcing = "retail"
        elif slug.endswith("-US"):
            sourcing = "domestic"
        else:
            sourcing = "overseas"

        needs_overseas_sku = sourcing == "domestic" and canonical_sku in bases_with_us
        name = " ".join(word.capitalize() for word in name_slug.split("-"))

        products.append({
            "sku": canonical_sku,
            "name": name,                    # fallback name from slug
            "product_url": prod_url,         # URL to scrape for full data
            "image_url": img_url or "",
            "sourcing": sourcing,
            "needs_overseas_sku": needs_overseas_sku,
        })

    return products


# ---------------------------------------------------------------------------
# Product page scraping  (playwright)
# ---------------------------------------------------------------------------

# JavaScript run inside each page via playwright to extract all product data
_EXTRACT_JS = """
(urlSku) => {
    // Build full text from ALL text nodes including hidden tab content
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {
        const txt = node.textContent.trim();
        if (txt) nodes.push(txt);
    }
    const t = nodes.join('\\n');

    const result = {};

    // Name from <h1>
    result.name = (document.querySelector('h1')?.textContent || '').trim();

    // Category: breadcrumb lines appear just before the product name
    const nameIdx = t.indexOf(result.name);
    const beforeName = t.substring(Math.max(0, nameIdx - 400), nameIdx);
    const bcLines = beforeName.split('\\n').map(l => l.trim()).filter(Boolean);
    const bcEnd = bcLines.length;
    // Second-to-last line before name = main category, last line = subcategory
    result.category = bcEnd >= 2 ? bcLines[bcEnd - 2] : (bcEnd >= 1 ? bcLines[bcEnd - 1] : '');
    result.subcategory = bcEnd >= 1 ? bcLines[bcEnd - 1] : '';

    // Colors: nodes between "Color" header and the SKU text node
    const skuIdx = nodes.findIndex(n => n === urlSku);
    let colorStart = -1;
    for (let i = skuIdx - 1; i >= Math.max(0, skuIdx - 20); i--) {
        if (nodes[i].toUpperCase() === 'COLOR') { colorStart = i; break; }
    }
    const colorNodes = colorStart > -1 ? nodes.slice(colorStart + 1, skuIdx) : [];
    const colors = colorNodes
        .filter(c => c.length < 30 && !/view all|more images|\\d/i.test(c))
        .join(', ');
    result.colors = colors;

    // MOQ
    const moqM = t.match(/\\bMOQ\\b\\n(\\d+)/);
    result.moq = moqM ? parseInt(moqM[1]) : 0;

    // Production time
    const ptM = t.match(/Production Time\\s*:?\\n?([\\w\\s,]+(?:days?|Days?)[^\\n]*)/i);
    result.productionTime = ptM ? ptM[1].trim() : '';

    // Description — between "Description" header and "MOQ"
    const descHeaderIdx = t.lastIndexOf('\\nDescription\\n');
    const moqIdx2 = t.indexOf('\\nMOQ\\n');
    result.description = (descHeaderIdx > -1 && moqIdx2 > descHeaderIdx)
        ? t.substring(descHeaderIdx + 13, moqIdx2)
            .replace(/\\n(Specifications|Imprint Details)\\n/g, '')
            .trim()
        : '';

    // Carton — website shows either "X Lbs / Y Kg" or "X lb." — store in kg/cm for NPDS
    const countM = t.match(/Count:\\n(\\d+)/);
    // Try "Lbs / Kg" format first, fall back to lbs-only and convert
    const weightKgM  = t.match(/Weight:\\n[\\d.]+\\s*Lbs?\\s*\\/\\s*([\\d.]+)\\s*Kg/i);
    const weightLbsM = t.match(/Weight:\\n([\\d.]+)\\s*Lbs?/i);
    let weightKg = 0;
    if (weightKgM)       weightKg = parseFloat(weightKgM[1]);
    else if (weightLbsM) weightKg = parseFloat(weightLbsM[1]) / 2.20462;
    // Dimensions come in inches — convert to cm (× 2.54)
    const dimM = t.match(/Dimensions:\\n([\\d.]+)"\\s*x\\s*([\\d.]+)"\\s*x\\s*([\\d.]+)"/);
    result.cartonQty    = countM ? parseInt(countM[1])               : 0;
    result.cartonWeight = parseFloat(weightKg.toFixed(2));
    result.cartonLength = dimM   ? parseFloat((parseFloat(dimM[1]) * 2.54).toFixed(2)) : 0;
    result.cartonWidth  = dimM   ? parseFloat((parseFloat(dimM[2]) * 2.54).toFixed(2)) : 0;
    result.cartonHeight = dimM   ? parseFloat((parseFloat(dimM[3]) * 2.54).toFixed(2)) : 0;

    // Packaging
    const packM = t.match(/\\nPackaging\\n([^\\n]+)/);
    result.packaging = packM ? packM[1].trim() : '';

    // Imprint location and dimension
    const impM = t.match(/Imprint Area\\n([\\w\\s]+?)\\n?-\\s*H\\s*([\\d.]+)"\\s*x\\s*W\\s*([\\d.]+)"/i);
    result.imprintLocation  = impM ? impM[1].trim() : '';
    result.imprintDimension = impM ? `H ${impM[2]}" x W ${impM[3]}"` : '';

    return result;
}
"""


def scrape_product_page(page, product_url, url_sku):
    """
    Navigate to product_url and extract structured product data.
    `page` is an open playwright Page object (reused across products).
    `url_sku` is the original URL slug SKU (e.g. "BA03-US") used to anchor color extraction.
    Returns a dict of product fields, or {} on failure.
    """
    try:
        page.goto(product_url, wait_until="networkidle", timeout=30000)
        data = page.evaluate(_EXTRACT_JS, url_sku)
        return data or {}
    except Exception as e:
        return {"_scrape_error": str(e)}


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------

def download_image(image_url):
    """Download image bytes from a CloudFront URL. Returns (filename, bytes)."""
    import urllib.parse
    # CloudFront filenames sometimes contain spaces — percent-encode the path only
    parsed = urllib.parse.urlparse(image_url)
    safe_path = urllib.parse.quote(parsed.path, safe="/")
    safe_url = parsed._replace(path=safe_path).geturl()
    with urllib.request.urlopen(safe_url, timeout=30, context=_SSL_CTX) as f:
        data = f.read()
    filename = parsed.path.rstrip("/").split("/")[-1].split("?")[0]
    # Sanitize filename — replace spaces and special chars
    filename = urllib.parse.quote(filename, safe=".-_")
    if not filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        filename = filename + ".jpg"
    return filename, data


def set_product_image(product, filename, image_bytes):
    """
    Save image to product.image (ImageField → Cloudinary via django-cloudinary-storage).
    Uses save=False on the field + queryset update to avoid triggering model.save() twice.
    """
    from django.core.files.base import ContentFile
    product.image.save(filename, ContentFile(image_bytes), save=False)
    Product.objects.filter(pk=product.pk).update(image=product.image.name)


# ---------------------------------------------------------------------------
# AI content generation  (shared with generate_web_content command)
# ---------------------------------------------------------------------------

def generate_description_for_product(product, api_key):
    """Generate a website-ready HTML product description via Claude Haiku."""
    import anthropic

    is_retail = product.sku.upper().startswith("RT") or product.sourcing == "retail"

    if is_retail:
        retail_instructions = """
RETAIL PRODUCT RULES (this is a genuine retail branded product):
- Identify the brand name and parent company from the product name/description.
- After all other content, append a trademark disclaimer paragraph using this exact format:
  <p class="trademark-notice"><em>[Brand] and [Product Name] are trademarks of [Parent Company], registered in the U.S. and other countries. LogoIncluded is not affiliated with or endorsed by [Parent Company].</em></p>
- Fill in [Brand], [Product Name], and [Parent Company] accurately (e.g. AirPods Pro → Apple Inc.).
- If there are multiple brand trademarks, include all in one sentence.
- Do NOT add a "SPECIAL ORDER:" prefix for retail products.
"""
    else:
        retail_instructions = """
- Do NOT use any brand names (Apple, Samsung, Google, etc.) in the description.
- If the product is a special/custom order, start the opening paragraph with: <strong>SPECIAL ORDER:</strong>
"""

    imprint_methods = product.imprint_methods.all() if product.pk else []
    methods_text = (
        ", ".join(m.name for m in imprint_methods)
        if imprint_methods
        else (product.imprint_method or "Not specified")
    )

    prompt = f"""You are a product copywriter for LogoIncluded, a promotional products company that sells custom-branded tech and lifestyle items.

Generate a website product description in HTML for the product below.

Follow this exact structure (copy the format precisely):

<p>Opening marketing sentence — lead with the product name and key selling points.</p>

<p><strong>KEY FEATURES:</strong></p>
<ul>
  <li><strong>Feature Label:</strong> Short benefit-focused description</li>
  ... (3–6 items)
</ul>

<p><strong>SPECIFICATIONS:</strong></p>
<ul>
  <li><strong>Spec Name:</strong> Value</li>
  ... (all relevant specs)
</ul>

<p>MOQ<br>{product.moq}</p>
<p>PRODUCTION TIME<br>{product.production_time}</p>

PRODUCT DATA:
Name: {product.name}
SKU: {product.sku}
Raw description / notes: {product.description}
Available Colors: {product.colors}
MOQ: {product.moq}
Production Time: {product.production_time}
Imprint Location: {product.imprint_location}
Imprint Methods: {methods_text}
Package: {product.package}

Rules:
- Return ONLY the raw HTML — no markdown, no code fences, no explanation
- Keep marketing language professional but enthusiastic
- If specs are sparse, expand sensibly from the product name and notes
- Do not invent specs you have no basis for
{retail_instructions}"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_keywords_for_product(product, api_key):
    """Generate comma-separated keyword phrases via Claude Haiku."""
    import anthropic

    is_retail = product.sku.upper().startswith("RT") or product.sourcing == "retail"

    if is_retail:
        brand_rule = (
            "5. This IS a genuine retail branded product — DO include the brand name, product name, "
            "model name, and any well-known product-specific terms (e.g. AirPods, Apple, MagSafe, "
            "Galaxy Buds, Samsung). These are exactly what customers search for."
        )
    else:
        brand_rule = (
            "5. Do NOT use brand names (e.g. Apple, Samsung, Google, MagSafe, iPhone) — "
            "this is a generic/custom promotional product, not a retail branded item."
        )

    prompt = f"""You are a product data specialist for LogoIncluded, a promotional products distributor.

Generate keyword phrases for the product below following these strict rules:
1. Up to 30 keyword phrases total
2. Each phrase must be 30 characters or fewer
3. The entire list joined with ", " must be 200 characters or fewer (including spaces and commas)
4. Each phrase should be one or two words only — no sentences
{brand_rule}
6. Do NOT include competitor supplier names, line names, or part numbers
7. Focus on words distributors would actually search for — use type, function, material, use case, audience
8. No keyword spamming — every phrase must be genuinely relevant
9. Prioritize the most important keywords first

PRODUCT DATA:
Name: {product.name}
SKU: {product.sku}
Description: {product.description}
Category: {product.category}
Colors: {product.colors}

Return ONLY a plain comma-separated list of keyword phrases — no numbering, no bullets, no explanation, no extra text.
Example format: wireless charger, power bank, tech gift, desk accessory, fast charge
"""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    phrases = [p.strip() for p in raw.split(",") if p.strip()]
    phrases = [p for p in phrases if len(p) <= 30]
    final = []
    total = 0
    for p in phrases:
        needed = len(p) + (2 if final else 0)
        if total + needed <= 200:
            final.append(p)
            total += needed
        else:
            break

    return ", ".join(final)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Import products from the logoincluded.com sitemap (scrapes full product data via Playwright)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview what would be imported without saving anything",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Only process the first N products (useful for testing)",
        )
        parser.add_argument(
            "--sku", nargs="+", metavar="SKU",
            help="Only process the specified canonical SKUs (e.g. --sku EC18 TT01)",
        )
        parser.add_argument(
            "--skip-images", action="store_true",
            help="Skip Cloudinary image upload (stores CloudFront URL in image_url instead)",
        )
        parser.add_argument(
            "--skip-generate", action="store_true",
            help="Skip AI description/keyword generation",
        )
        parser.add_argument(
            "--skip-scrape", action="store_true",
            help="Skip Playwright page scraping (imports with name/sourcing only)",
        )

    def handle(self, *args, **options):
        import os

        dry_run       = options["dry_run"]
        limit         = options["limit"]
        only_skus     = {s.upper() for s in options["sku"]} if options["sku"] else None
        skip_images   = options["skip_images"]
        skip_generate = options["skip_generate"]
        skip_scrape   = options["skip_scrape"]
        api_key       = os.environ.get("ANTHROPIC_API_KEY", "")

        if not skip_generate and not api_key:
            self.stderr.write(self.style.WARNING(
                "ANTHROPIC_API_KEY not set — AI generation will be skipped."
            ))
            skip_generate = True

        # ── 1. Fetch sitemap ──────────────────────────────────────────────
        self.stdout.write("Fetching sitemap from logoincluded.com...")
        try:
            products_data = fetch_sitemap_products()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to fetch sitemap: {e}"))
            return

        self.stdout.write(f"Sitemap contains {len(products_data)} importable products")

        # ── 2. Apply filters ──────────────────────────────────────────────
        if only_skus:
            products_data = [p for p in products_data if p["sku"] in only_skus]
            self.stdout.write(f"Filtered to {len(products_data)} specified SKU(s)")

        if limit:
            products_data = products_data[:limit]
            self.stdout.write(f"Limited to first {limit} product(s)")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — nothing will be saved\n"))

        # ── 3. Import loop ────────────────────────────────────────────────
        created = skipped = errors = 0

        # Playwright uses greenlet internally, which Django mistakes for an async context.
        # Setting this flag tells Django to allow synchronous ORM calls anyway — safe here
        # because we are in a management command, not an actual async event loop.
        import os as _os
        _os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        # Open a single Playwright browser for the whole run
        pw_browser = pw_page = None
        if not skip_scrape and not dry_run:
            try:
                from playwright.sync_api import sync_playwright
                _pw = sync_playwright().start()
                pw_browser = _pw.chromium.launch(headless=True)
                pw_page = pw_browser.new_page()
                self.stdout.write("Playwright browser launched ✓")
            except Exception as e:
                self.stderr.write(self.style.WARNING(
                    f"Could not launch Playwright ({e}) — page scraping will be skipped. "
                    "Run: pip install playwright && playwright install chromium"
                ))
                skip_scrape = True

        try:
            for i, data in enumerate(products_data, 1):
                sku = data["sku"]
                # The original URL slug SKU (with -US if applicable) — needed for color anchor
                url_slug_sku = data["product_url"].rstrip("/").split("/")[-1].upper()
                label = f"[{i}/{len(products_data)}] {sku} ({data['sourcing']})"

                if Product.objects.filter(sku=sku).exists():
                    self.stdout.write(f"  {label} — already exists, skipping")
                    skipped += 1
                    continue

                self.stdout.write(f"  {label} — {data['name']}")

                if dry_run:
                    flags = []
                    if data["needs_overseas_sku"]:
                        flags.append("needs_overseas_sku")
                    if data["image_url"]:
                        flags.append("has image")
                    self.stdout.write(f"    would create  {', '.join(flags) or 'no flags'}")
                    created += 1
                    continue

                try:
                    # ── Scrape product page ──
                    scraped = {}
                    if not skip_scrape and pw_page:
                        self.stdout.write(f"    scraping product page...", ending="\r")
                        scraped = scrape_product_page(pw_page, data["product_url"], url_slug_sku)
                        if scraped.get("_scrape_error"):
                            self.stderr.write(f"    scrape warning: {scraped['_scrape_error']}")
                            scraped = {}
                        else:
                            self.stdout.write(f"    scraped: {scraped.get('name', '?')} | "
                                              f"MOQ={scraped.get('moq',0)} | "
                                              f"colors={scraped.get('colors','—')[:30]}")

                    # ── Download image (before product save) ──
                    img_filename = img_bytes = None
                    if not skip_images and data["image_url"]:
                        try:
                            img_filename, img_bytes = download_image(data["image_url"])
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"    image download failed: {e}"))

                    # ── Create product record ──
                    product = Product(
                        sku=sku,
                        name=(scraped.get("name") or data["name"])[:150],
                        sourcing=data["sourcing"],
                        needs_overseas_sku=data["needs_overseas_sku"],
                        # image_url kept as CloudFront fallback; product.image set below
                        image_url=data["image_url"],
                        # Status and checkboxes for imported/published products
                        status="Published",
                        price_list=True,
                        npds_done=False,   # leave blank — marketing fills in
                        qb_added=True,
                        # From scraper (default 0/"" if scraping failed)
                        # All CharField values are truncated to model max_length to prevent
                        # "value too long for type character varying(N)" DB errors
                        description=scraped.get("description", "")[:500],
                        colors=scraped.get("colors", "")[:150],
                        moq=scraped.get("moq", 0),
                        production_time=scraped.get("productionTime", "")[:50],
                        package=scraped.get("packaging", "")[:50],
                        carton_qty=scraped.get("cartonQty", 0),
                        carton_weight=scraped.get("cartonWeight", 0),
                        carton_width=scraped.get("cartonWidth", 0),
                        carton_length=scraped.get("cartonLength", 0),
                        carton_height=scraped.get("cartonHeight", 0),
                        imprint_location=scraped.get("imprintLocation", "")[:50],
                        imprint_dimension=scraped.get("imprintDimension", "")[:50],
                        category=scraped.get("category", "")[:50],
                        # Fields left blank — filled in later
                        vendor="",
                        vendor_sku="",
                        estimated_launch="",
                        imprint_method="",
                        air_freight=0,
                        ocean_freight=0,
                        duty_percent=0,
                        tariff_percent=0,
                    )
                    product.save()

                    # ── Upload image to Cloudinary via ImageField ──
                    if img_filename and img_bytes:
                        try:
                            set_product_image(product, img_filename, img_bytes)
                            self.stdout.write(self.style.SUCCESS(f"    image uploaded ✓"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"    image upload failed: {e}"))

                    # ── AI generation ──
                    if not skip_generate:
                        try:
                            product.website_description = generate_description_for_product(product, api_key)
                            product.website_keywords = generate_keywords_for_product(product, api_key)
                            product.save(update_fields=["website_description", "website_keywords"])
                            self.stdout.write(f"    AI content generated ✓")
                            time.sleep(0.5)
                        except Exception as e:
                            self.stderr.write(f"    AI generation failed: {e}")

                    created += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✓ created"))

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"    ✗ error: {e}"))
                    errors += 1

        finally:
            if pw_browser:
                pw_browser.close()

        # ── 4. Summary ────────────────────────────────────────────────────
        self.stdout.write("\n" + "─" * 40)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN complete"))
            self.stdout.write(f"  Would create : {created}")
            self.stdout.write(f"  Would skip   : {skipped} (already in DB)")
        else:
            self.stdout.write(self.style.SUCCESS("Import complete"))
            self.stdout.write(f"  Created : {created}")
            self.stdout.write(f"  Skipped : {skipped} (already in DB)")
            self.stdout.write(f"  Errors  : {errors}")
