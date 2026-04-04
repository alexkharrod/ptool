import base64
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import CreateProductForm
from .models import Product, Vendor, HtsCode


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
            return redirect("view_product", pk=product.pk)
    else:
        form = CreateProductForm(instance=product)
    return render(request, "edit_product.html", {"form": form, "product": product})


@login_required
def products(request):
    search_query = request.GET.get("search", "")
    # Default to Open when browsing; search across all statuses when text search is active
    status_filter = request.GET.get("status", "Open" if not search_query else "")

    sort = request.GET.get("sort", "date_created")
    direction = request.GET.get("dir", "desc")

    allowed_sorts = {"sku", "name", "category", "status", "date_created"}
    if sort not in allowed_sorts:
        sort = "sku"
    if direction not in ("asc", "desc"):
        direction = "asc"

    queryset = Product.objects.all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if search_query:
        queryset = queryset.filter(
            Q(sku__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
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
            product = form.save()
            return redirect("view_product", pk=product.pk)
    else:
        form = CreateProductForm()
    return render(request, "add_product.html", {"form": form})


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
        notes = request.POST.get("other_tariff_notes", "").strip()
        category_hint = request.POST.get("category_hint", "")
        if not code or not description:
            error = "HTS code and description are required."
        elif HtsCode.objects.filter(code=code).exists():
            error = f'HTS code "{code}" already exists.'
        else:
            HtsCode.objects.create(
                code=code, description=description,
                duty_percent=duty, section_301_percent=s301,
                other_tariff_notes=notes, category_hint=category_hint,
            )
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
def toggle_product_flag(request, pk):
    import json
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        allowed_fields = {"price_list", "product_list", "hts_list", "npds_done", "qb_added", "published"}
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
