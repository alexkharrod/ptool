import base64
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .forms import CreateProductForm
from .models import Product, Category


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
    category_filter = request.GET.get("category", "")

    queryset = Product.objects.all()

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    if category_filter:
        queryset = queryset.filter(category=category_filter)

    if search_query:
        queryset = queryset.filter(
            Q(sku__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(vendor__icontains=search_query)
        )

    queryset = queryset.order_by("sku")

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "products": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "category_filter": category_filter,
        "status_choices": Product.STATUS_CHOICES,
        "categories": Category.objects.order_by("code"),
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
        import urllib.request
        image_url = product.image.url
        if image_url.startswith("/"):
            image_url = request.build_absolute_uri(image_url)
        with urllib.request.urlopen(image_url) as resp:
            encoded_image = base64.b64encode(resp.read()).decode("utf-8")
    elif product.image_url:
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


# ─── Category management ──────────────────────────────────────────────────────

@login_required
def categories(request):
    """List all categories with add and delete."""
    error = None
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        if not code:
            error = "Category code cannot be blank."
        elif Category.objects.filter(code=code).exists():
            error = f'"{code}" already exists.'
        else:
            Category.objects.create(code=code)
            return redirect("categories")
    all_categories = Category.objects.order_by("code")
    return render(request, "categories.html", {"categories": all_categories, "error": error})


@login_required
@require_POST
def delete_category(request, pk):
    """Delete a category — only if no products are using it."""
    cat = get_object_or_404(Category, pk=pk)
    if Product.objects.filter(category=cat.code).exists():
        count = Product.objects.filter(category=cat.code).count()
        # Redirect back with an error message via query param
        return redirect(f"/products/categories/?error={cat.code}+is+used+by+{count}+product(s)+and+cannot+be+deleted.")
    cat.delete()
    return redirect("categories")


@login_required
@require_POST
def add_category_ajax(request):
    """AJAX endpoint — adds a category and returns JSON for the modal on product forms."""
    code = request.POST.get("code", "").strip().upper()
    if not code:
        return JsonResponse({"success": False, "error": "Code cannot be blank."})
    if Category.objects.filter(code=code).exists():
        return JsonResponse({"success": False, "error": f'"{code}" already exists.'})
    Category.objects.create(code=code)
    return JsonResponse({"success": True, "code": code})
