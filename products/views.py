import base64
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string

from .forms import CreateProductForm
from .models import Product


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
    status_filter = request.GET.get("status", "Open")

    sort = request.GET.get("sort", "sku")
    direction = request.GET.get("dir", "asc")

    allowed_sorts = {"sku", "name", "category", "status"}
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
