import base64
import json
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import CreateProductForm
from .models import Category, ImprintMethod, Product, Vendor, HtsCode


@login_required
def next_sku(request):
    """Return the next available SKU for a given category code."""
    import re
    code = request.GET.get("category", "").strip().upper()
    if not code:
        return JsonResponse({"error": "No category provided"}, status=400)
    try:
        category = Category.objects.get(code=code)
    except Category.DoesNotExist:
        return JsonResponse({"error": "Category not found"}, status=404)

    # Find all SKUs that start with this category code followed by digits
    pattern = re.compile(r"^" + re.escape(code) + r"(\d+)$", re.IGNORECASE)
    existing_nums = []
    for sku in Product.objects.filter(sku__istartswith=code).values_list("sku", flat=True):
        m = pattern.match(sku)
        if m:
            existing_nums.append(int(m.group(1)))

    if existing_nums:
        next_num = max(existing_nums) + 1
    else:
        next_num = category.sku_seed

    # Walk forward until we find a SKU that doesn't exist (handles gaps/manual entries)
    all_skus = set(Product.objects.filter(sku__istartswith=code).values_list("sku", flat=True))
    while f"{code}{next_num}" in all_skus:
        next_num += 1

    return JsonResponse({"sku": f"{code}{next_num}"})


@login_required
def view_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, "view_product.html", {"product": product})


@login_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = CreateProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            back = request.POST.get("back", "")
            if back and back.startswith("/"):
                return redirect(back)
            return redirect("view_product", pk=product.pk)
    else:
        form = CreateProductForm(instance=product)
    hts_data = {h.pk: {"duty": float(h.duty_percent), "section301": float(h.section_301_percent), "extra": float(h.extra_tariff_percent), "total": float(h.total_percent)} for h in HtsCode.objects.all()}
    imprint_methods_data = list(ImprintMethod.objects.values("name", "setup_fee", "run_charge"))
    return render(request, "edit_product.html", {
        "form": form,
        "product": product,
        "hts_data": json.dumps(hts_data),
        "imprint_methods_data": imprint_methods_data,
    })


@login_required
def products(request):
    search_query = request.GET.get("search", "")

    # "active" is a synthetic filter that shows Open + Quote Only together.
    # When a text search is active we show all statuses so nothing is hidden.
    # Explicit status= param overrides everything.
    if "status" in request.GET:
        status_filter = request.GET.get("status", "")
    elif search_query:
        status_filter = ""   # show all when searching
    else:
        status_filter = "Open"  # default: Open only

    sort = request.GET.get("sort", "date_created")
    direction = request.GET.get("dir", "desc")

    allowed_sorts = {"sku", "name", "category", "status", "date_created", "price_list", "npds_done", "qb_added"}
    if sort not in allowed_sorts:
        sort = "sku"
    if direction not in ("asc", "desc"):
        direction = "asc"

    queryset = Product.objects.all()

    if status_filter == "active":
        queryset = queryset.filter(status__in=["Open", "Quote Only"])
    elif status_filter:
        queryset = queryset.filter(status=status_filter)

    if search_query:
        queryset = queryset.filter(
            Q(sku__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(vendor_sku__icontains=search_query)
            | Q(vendor__icontains=search_query)
            | Q(vendor_ref__name__icontains=search_query)
        )

    order_field = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_field)

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "products": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "status_choices": Product.STATUS_CHOICES,
        "sort": sort,
        "dir": direction,
    }

    return render(request, "products.html", context)


@login_required
def add_product(request):
    if request.method == "POST":
        form = CreateProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = form.save()
                return redirect("view_product", pk=product.pk)
            except Exception as e:
                if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                    form.add_error("sku", "That SKU already exists — please choose a different one.")
                else:
                    form.add_error(None, f"Could not save product: {e}")
    else:
        form = CreateProductForm()
    hts_data = {h.pk: {"duty": float(h.duty_percent), "section301": float(h.section_301_percent), "extra": float(h.extra_tariff_percent), "total": float(h.total_percent)} for h in HtsCode.objects.all()}
    imprint_methods_data = list(ImprintMethod.objects.values("name", "setup_fee", "run_charge"))
    return render(request, "add_product.html", {
        "form": form,
        "hts_data": json.dumps(hts_data),
        "imprint_methods_data": imprint_methods_data,
    })


@login_required
def npds(request, product_id):
    from weasyprint import HTML  # lazy import — avoids crash if system libs missing at startup

    product = get_object_or_404(Product, id=product_id)

    encoded_image = ""
    if product.image:
        # Fetch image from Cloudinary (or local media) URL
        import urllib.request
        image_url = product.image.url
        # If URL is relative (local dev), make it absolute
        if image_url.startswith("/"):
            image_url = request.build_absolute_uri(image_url)
        with urllib.request.urlopen(image_url) as resp:
            encoded_image = base64.b64encode(resp.read()).decode("utf-8")
    elif product.image_url:
        # Fallback: read from static/images/ for products not yet migrated
        image_path = os.path.join(settings.BASE_DIR, "static", "images", product.image_url)
        if os.path.isfile(image_path):
            with open(image_path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

    context = {"product": product, "encoded_image": encoded_image}

    html_string = render_to_string("npds.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="NPDS_{product.sku}.pdf"'

    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(
        response, presentational_hints=True
    )

    return response


@login_required
def bulk_update_products(request):
    if request.method == "POST":
        product_ids = request.POST.getlist("product_ids")
        new_status = request.POST.get("bulk_status")
        valid_statuses = [s[0] for s in Product.STATUS_CHOICES]
        if new_status in valid_statuses and product_ids:
            updated = Product.objects.filter(pk__in=product_ids).update(status=new_status)
            from django.contrib import messages
            messages.success(request, f"{updated} product(s) updated to {new_status}.")
        else:
            from django.contrib import messages
            messages.error(request, "Please select products and a valid status.")
    params = request.POST.get("return_params", "")
    return redirect(f"/products/?{params}")


# ── HTS AI Suggest ────────────────────────────────────────────────────────────

@login_required
def hts_ai_suggest(request, pk):
    """
    Call Claude with the product's name, description, category, and image
    to suggest the best HTS code + tariff rates. Returns JSON.
    """
    import urllib.request as urlreq
    import anthropic
    from django.conf import settings

    product = get_object_or_404(Product, pk=pk)

    # Build text context
    lines = []
    if product.name:
        lines.append(f"Product name: {product.name}")
    if product.category:
        lines.append(f"Category: {product.category}")
    if product.description:
        lines.append(f"Description: {product.description[:800]}")
    if product.vendor:
        lines.append(f"Vendor/brand context: {product.vendor}")
    product_text = "\n".join(lines) if lines else "No description provided."

    prompt = (
        "You are a US import/export compliance specialist with deep expertise in the "
        "Harmonized Tariff Schedule (HTS). Analyze this promotional product and return "
        "the most appropriate 10-digit HTS code with current tariff rates.\n\n"
        f"{product_text}\n\n"
        "Return ONLY a valid JSON object — no markdown, no explanation outside the JSON:\n"
        "{\n"
        '  "hts_code": "XXXX.XX.XXXX",\n'
        '  "description": "HTS line description",\n'
        '  "duty_percent": 0.0,\n'
        '  "section_301_percent": 0.0,\n'
        '  "extra_tariff_percent": 10.0,\n'
        '  "reasoning": "1-2 sentence explanation of why this code applies",\n'
        '  "confidence": "high | medium | low"\n'
        "}\n\n"
        "Rules:\n"
        "- duty_percent: standard MFN duty rate for this HTS code\n"
        "- section_301_percent: Section 301 tariff (typically 25% for most Chinese goods, 0% if not subject)\n"
        "- extra_tariff_percent: Additional executive tariff currently in effect (10% baseline as of early 2025, "
        "may be higher for specific categories — use your best current knowledge)\n"
        "- Be precise with the 10-digit HTS code; promotional/advertising products often have specific subheadings"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        content = []

        # Include product image if available
        if product.image:
            try:
                with urlreq.urlopen(product.image.url, timeout=5) as resp:
                    image_bytes = resp.read()
                import base64
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.b64encode(image_bytes).decode(),
                    }
                })
            except Exception:
                pass  # Image unavailable — continue with text only

        content.append({"type": "text", "text": prompt})

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": content}],
        )

        raw = message.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        suggested = json.loads(raw)

        # Try to match against an existing HTS code in our DB
        code_clean = suggested.get("hts_code", "").replace("-", "").replace(" ", "")
        existing = HtsCode.objects.filter(code__iexact=code_clean).first()
        if not existing:
            # Try prefix match (first 8 digits)
            existing = HtsCode.objects.filter(code__startswith=code_clean[:8]).first()

        suggested["in_db"] = existing is not None
        if existing:
            suggested["db_id"] = existing.pk
            suggested["db_code"] = existing.code
            suggested["db_description"] = existing.description
            suggested["db_duty"] = float(existing.duty_percent)
            suggested["db_section301"] = float(existing.section_301_percent)
            suggested["db_extra"] = float(existing.extra_tariff_percent)
            suggested["db_total"] = float(existing.total_percent)

        return JsonResponse({"ok": True, **suggested})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
def hts_ai_suggest_text(request):
    """
    Same as hts_ai_suggest but accepts name/category/description as POST text
    (for use on add_product before the product is saved).
    """
    import anthropic
    from django.conf import settings

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    data = json.loads(request.body)
    name = data.get("name", "")
    category = data.get("category", "")
    description = data.get("description", "")

    lines = []
    if name:        lines.append(f"Product name: {name}")
    if category:    lines.append(f"Category: {category}")
    if description: lines.append(f"Description: {description[:800]}")
    product_text = "\n".join(lines) if lines else "No description provided."

    prompt = (
        "You are a US import/export compliance specialist with deep expertise in the "
        "Harmonized Tariff Schedule (HTS). Analyze this promotional product and return "
        "the most appropriate 10-digit HTS code with current tariff rates.\n\n"
        f"{product_text}\n\n"
        "Return ONLY a valid JSON object — no markdown, no explanation outside the JSON:\n"
        "{\n"
        '  "hts_code": "XXXX.XX.XXXX",\n'
        '  "description": "HTS line description",\n'
        '  "duty_percent": 0.0,\n'
        '  "section_301_percent": 0.0,\n'
        '  "extra_tariff_percent": 10.0,\n'
        '  "reasoning": "1-2 sentence explanation of why this code applies",\n'
        '  "confidence": "high | medium | low"\n'
        "}\n\n"
        "Rules:\n"
        "- duty_percent: standard MFN duty rate for this HTS code\n"
        "- section_301_percent: Section 301 tariff (typically 25% for most Chinese goods, 0% if not subject)\n"
        "- extra_tariff_percent: Additional executive tariff currently in effect (10% baseline as of early 2025, "
        "may be higher for specific categories — use your best current knowledge)\n"
        "- Be precise with the 10-digit HTS code"
    )

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        suggested = json.loads(raw)

        code_clean = suggested.get("hts_code", "").replace("-", "").replace(" ", "")
        existing = HtsCode.objects.filter(code__iexact=code_clean).first()
        if not existing:
            existing = HtsCode.objects.filter(code__startswith=code_clean[:8]).first()

        suggested["in_db"] = existing is not None
        if existing:
            suggested["db_id"] = existing.pk
            suggested["db_code"] = existing.code
            suggested["db_description"] = existing.description
            suggested["db_duty"] = float(existing.duty_percent)
            suggested["db_section301"] = float(existing.section_301_percent)
            suggested["db_extra"] = float(existing.extra_tariff_percent)
            suggested["db_total"] = float(existing.total_percent)

        return JsonResponse({"ok": True, **suggested})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ── Reports ───────────────────────────────────────────────────────────────────

@login_required
def report_index(request):
    return render(request, "reports/index.html")


@login_required
def report_show_roi(request):
    from scouting.models import Prospect
    from django.db.models import Count, Q, Min, Max

    shows = (
        Prospect.objects
        .values("show_name")
        .annotate(
            show_date=Min("show_date"),
            total=Count("id"),
            promoted=Count("id", filter=Q(promoted=True)),
            rejected=Count("id", filter=Q(status="Rejected")),
            spotted=Count("id", filter=Q(status="Spotted")),
            sample_ordered=Count("id", filter=Q(status="Sample Ordered")),
            evaluating=Count("id", filter=Q(status="Evaluating")),
        )
        .order_by("-show_date", "show_name")
    )

    shows = list(shows)
    total_prospects = sum(s["total"] for s in shows)
    total_promoted = sum(s["promoted"] for s in shows)
    overall_rate = round(total_promoted / total_prospects * 100, 1) if total_prospects else 0

    for show in shows:
        show["active"] = show["total"] - show["promoted"] - show["rejected"]
        show["rate"] = (
            round(show["promoted"] / show["total"] * 100, 1)
            if show["total"] > 0 else 0
        )
        show["products"] = list(
            Product.objects
            .filter(source_show=show["show_name"])
            .values("pk", "sku", "name", "status")
            .order_by("sku")
        )

    return render(request, "reports/show_roi.html", {
        "shows": shows,
        "total_prospects": total_prospects,
        "total_promoted": total_promoted,
        "overall_rate": overall_rate,
    })


@login_required
def report_published(request):
    import datetime

    date_from_str = request.GET.get("from", "")
    date_to_str = request.GET.get("to", "")

    queryset = Product.objects.filter(status="Published").order_by("-date_published", "-date_created")

    if date_from_str:
        try:
            queryset = queryset.filter(date_published__date__gte=date_from_str)
        except Exception:
            pass
    if date_to_str:
        try:
            queryset = queryset.filter(date_published__date__lte=date_to_str)
        except Exception:
            pass

    total = queryset.count()
    by_show = (
        queryset.exclude(source_show="")
        .values("source_show")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    today = datetime.date.today()
    days_90_ago = (today - datetime.timedelta(days=90)).isoformat()
    month_start = today.replace(day=1).isoformat()
    year_start = today.replace(month=1, day=1).isoformat()
    today_str = today.isoformat()

    return render(request, "reports/published.html", {
        "products": queryset,
        "date_from": date_from_str,
        "date_to": date_to_str,
        "total": total,
        "by_show": by_show,
        "days_90_ago": days_90_ago,
        "month_start": month_start,
        "year_start": year_start,
        "today_str": today_str,
    })


@login_required
def hts_list(request):
    codes = HtsCode.objects.annotate(product_count=models.Count("products")).order_by("code")
    return render(request, "hts/hts_list.html", {"codes": codes})


@login_required
def hts_add(request):
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        description = request.POST.get("description", "").strip()
        duty = request.POST.get("duty_percent", "0")
        s301 = request.POST.get("section_301_percent", "0")
        extra = request.POST.get("extra_tariff_percent", "0")
        notes = request.POST.get("other_tariff_notes", "").strip()
        category_hint = request.POST.get("category_hint", "")
        if not code or not description:
            error = "HTS code and description are required."
        elif HtsCode.objects.filter(code=code).exists():
            error = f'HTS code "{code}" already exists.'
        else:
            hts = HtsCode.objects.create(
                code=code, description=description,
                duty_percent=duty, section_301_percent=s301,
                extra_tariff_percent=extra,
                other_tariff_notes=notes, category_hint=category_hint,
            )
            # AJAX request from HTS AI suggest — return JSON instead of redirecting
            if request.POST.get("_ajax") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "id": hts.pk, "code": hts.code})
            return redirect("hts_list")
    return render(request, "hts/hts_add.html", {
        "error": error,
        "category_choices": HtsCode.CATEGORY_CHOICES,
        "post": request.POST,
    })


@login_required
def hts_edit(request, pk):
    hts = get_object_or_404(HtsCode, pk=pk)
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        description = request.POST.get("description", "").strip()
        duty = request.POST.get("duty_percent", "0")
        s301 = request.POST.get("section_301_percent", "0")
        extra = request.POST.get("extra_tariff_percent", "0")
        notes = request.POST.get("other_tariff_notes", "").strip()
        category_hint = request.POST.get("category_hint", "")
        if not code or not description:
            error = "HTS code and description are required."
        elif HtsCode.objects.filter(code=code).exclude(pk=pk).exists():
            error = f'HTS code "{code}" already exists.'
        else:
            hts.code = code
            hts.description = description
            hts.duty_percent = duty
            hts.section_301_percent = s301
            hts.extra_tariff_percent = extra
            hts.other_tariff_notes = notes
            hts.category_hint = category_hint
            hts.save()
            return redirect("hts_list")
    return render(request, "hts/hts_edit.html", {
        "hts": hts,
        "error": error,
        "category_choices": HtsCode.CATEGORY_CHOICES,
        "post": request.POST,
    })


@login_required
def hts_suggest(request):
    """AJAX endpoint: returns HTS codes matching a category or search term."""
    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    qs = HtsCode.objects.all()
    if category:
        qs = qs.filter(category_hint=category)
    if q:
        qs = qs.filter(
            models.Q(code__icontains=q) | models.Q(description__icontains=q)
        )
    results = list(qs.values("id", "code", "description", "duty_percent", "section_301_percent", "other_tariff_notes")[:20])
    return JsonResponse({"results": results})


@login_required
def vendor_list(request):
    vendors = Vendor.objects.annotate(product_count=models.Count("products")).order_by("name")
    return render(request, "vendors/vendor_list.html", {"vendors": vendors})


@login_required
def vendor_add(request):
    error = None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        country = request.POST.get("country", "CN")
        if not name:
            error = "Vendor name is required."
        elif Vendor.objects.filter(name__iexact=name).exists():
            error = f'A vendor named "{name}" already exists.'
        else:
            Vendor.objects.create(name=name, country=country)
            return redirect("vendor_list")
    return render(request, "vendors/vendor_add.html", {
        "error": error,
        "country_choices": Vendor.COUNTRY_CHOICES,
    })


@login_required
def vendor_edit(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk)
    error = None
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        country = request.POST.get("country", "CN")
        if not name:
            error = "Vendor name is required."
        elif Vendor.objects.filter(name__iexact=name).exclude(pk=pk).exists():
            error = f'A vendor named "{name}" already exists.'
        else:
            vendor.name = name
            vendor.country = country
            vendor.save()
            return redirect("vendor_list")
    return render(request, "vendors/vendor_edit.html", {
        "vendor": vendor,
        "error": error,
        "country_choices": Vendor.COUNTRY_CHOICES,
    })


@login_required
def generate_description(request, pk):
    """Call Claude to generate a website-ready HTML product description."""
    import anthropic, os

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    product = get_object_or_404(Product, pk=pk)

    imprint_methods = product.imprint_methods.all()
    methods_text = (
        ", ".join(m.name for m in imprint_methods)
        if imprint_methods.exists()
        else (product.imprint_method or "Not specified")
    )

    is_retail = product.sku.upper().startswith("RT") or product.sourcing == "retail"

    if is_retail:
        retail_instructions = """
RETAIL PRODUCT RULES (this is a genuine retail branded product):
- Identify the brand name and parent company from the product name/description.
- After all other content, append a trademark disclaimer paragraph using this exact format:
  <p class="trademark-notice"><em>[Brand] and [Product Name] are trademarks of [Parent Company], registered in the U.S. and other countries. LogoIncluded is not affiliated with or endorsed by [Parent Company].</em></p>
- Fill in [Brand], [Product Name], and [Parent Company] accurately (e.g. AirPods Pro → Apple Inc.; Galaxy Buds → Samsung Electronics Co., Ltd.).
- If there are multiple brand trademarks (e.g. MagSafe + Apple), include all in one sentence.
- Do NOT add a "SPECIAL ORDER:" prefix for retail products.
"""
    else:
        retail_instructions = """
- Do NOT use any brand names (Apple, Samsung, Google, etc.) in the description.
- If the product is a special/custom order, start the opening paragraph with: <strong>SPECIAL ORDER:</strong>
"""

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

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "ANTHROPIC_API_KEY not configured"}, status=500)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    html_output = message.content[0].text.strip()

    # Save to database
    product.website_description = html_output
    product.save(update_fields=["website_description"])

    return JsonResponse({"html": html_output})


@login_required
def generate_keywords(request, pk):
    """Call Claude to generate PromoStandards-compliant product keywords."""
    import anthropic, os

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    product = get_object_or_404(Product, pk=pk)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return JsonResponse({"error": "ANTHROPIC_API_KEY not configured"}, status=500)

    is_retail = product.sku.upper().startswith("RT") or product.sourcing == "retail"

    if is_retail:
        brand_rule = (
            "5. This IS a genuine retail branded product — DO include the brand name, product name, "
            "model name, and any well-known product-specific terms (e.g. AirPods, Apple, MagSafe, "
            "Galaxy Buds, Samsung). These are exactly what customers search for."
        )
        no_brand_note = ""
    else:
        brand_rule = (
            "5. Do NOT use brand names (e.g. Apple, Samsung, Google, MagSafe, iPhone) — "
            "this is a generic/custom promotional product, not a retail branded item."
        )
        no_brand_note = ""

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
9. Prioritize the most important keywords first — if the list must be trimmed to fit 200 characters, keep the best ones

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

    # Parse into list, enforce per-phrase and total character limits
    phrases = [p.strip() for p in raw.split(",") if p.strip()]
    phrases = [p for p in phrases if len(p) <= 30]

    # Enforce 200-char total limit (joined as "phrase1, phrase2, ...")
    final = []
    total = 0
    for p in phrases:
        needed = len(p) + (2 if final else 0)  # ", " separator except for first
        if total + needed <= 200:
            final.append(p)
            total += needed
        else:
            break
    phrases = final[:30]

    # Save to database
    product.website_keywords = ", ".join(phrases)
    product.save(update_fields=["website_keywords"])

    return JsonResponse({"keywords": phrases, "raw": ", ".join(phrases)})


@login_required
def product_web_content(request, pk):
    """Return saved website description and keywords as JSON (for the product list modal)."""
    product = get_object_or_404(Product, pk=pk)
    return JsonResponse({
        "sku": product.sku,
        "name": product.name,
        "description": product.website_description or "",
        "keywords": product.website_keywords or "",
    })


@login_required
def toggle_product_flag(request, pk):
    import json
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        allowed_fields = {"price_list", "npds_done", "qb_added"}
        try:
            data = json.loads(request.body)
            field = data.get("field")
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({"ok": False, "error": "Invalid request"}, status=400)
        if field not in allowed_fields:
            return JsonResponse({"ok": False, "error": "Invalid field"}, status=400)
        new_val = not getattr(product, field)
        setattr(product, field, new_val)
        product.save(update_fields=[field])
        return JsonResponse({"ok": True, "value": new_val})
    return JsonResponse({"ok": False}, status=405)


# ── Category management ────────────────────────────────────────────────────────

@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, "categories/category_list.html", {"categories": categories})


@login_required
def category_add(request):
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        description = request.POST.get("description", "").strip()
        if not code or not description:
            error = "Code and description are required."
        elif Category.objects.filter(code__iexact=code).exists():
            error = f'Category code "{code}" already exists.'
        else:
            Category.objects.create(code=code, description=description)
            return redirect("category_list")
    return render(request, "categories/category_add.html", {"error": error, "post": request.POST})


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        description = request.POST.get("description", "").strip()
        if not code or not description:
            error = "Code and description are required."
        elif Category.objects.filter(code__iexact=code).exclude(pk=pk).exists():
            error = f'Category code "{code}" already exists.'
        else:
            category.code = code
            category.description = description
            category.save()
            return redirect("category_list")
    return render(request, "categories/category_edit.html", {"category": category, "error": error})
