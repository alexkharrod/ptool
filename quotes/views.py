import base64
import json
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.timezone import now

from products.models import HtsCode
from .forms import CreateQuoteForm
from .models import Quote


@login_required
def view_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    return render(request, "view_quote.html", {"quote": quote, "status_choices": Quote.STATUS_CHOICES})


@login_required
def update_quote_status(request, pk):
    if request.method == "POST":
        quote = get_object_or_404(Quote, pk=pk)
        new_status = request.POST.get("status")
        valid_statuses = [s[0] for s in Quote.STATUS_CHOICES]
        if new_status in valid_statuses:
            quote.status = new_status
            quote.save()
            messages.success(request, f"Status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status.")
    return redirect("view_quote", pk=pk)


@login_required
def bulk_update_quotes(request):
    if request.method == "POST":
        quote_ids = request.POST.getlist("quote_ids")
        new_status = request.POST.get("bulk_status")
        valid_statuses = [s[0] for s in Quote.STATUS_CHOICES]
        if new_status in valid_statuses and quote_ids:
            updated = Quote.objects.filter(pk__in=quote_ids).update(status=new_status)
            messages.success(request, f"{updated} quote(s) updated to {new_status}.")
        else:
            messages.error(request, "Please select quotes and a valid status.")
    # Preserve current query params when redirecting back
    params = request.POST.get("return_params", "")
    return redirect(f"/quotes/quotes/?{params}")


@login_required
def edit_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == "POST":
        form = CreateQuoteForm(request.POST, request.FILES, instance=quote)
        if form.is_valid():
            form.save()
            return redirect("view_quote", pk=quote.pk)
    else:
        form = CreateQuoteForm(instance=quote)
    hts_data = {h.pk: {"duty": float(h.duty_percent), "section301": float(h.section_301_percent), "extra": float(h.extra_tariff_percent), "total": float(h.total_percent)} for h in HtsCode.objects.all()}
    return render(request, "edit_quote.html", {"form": form, "quote": quote, "hts_data": json.dumps(hts_data)})


@login_required
def quotes(request):
    search_query = request.GET.get("search", "")
    # Default to Open when browsing; search across all statuses when text search is active
    status_filter = request.GET.get("status", "Open" if not search_query else "all")

    sort = request.GET.get("sort", "date_created")
    direction = request.GET.get("dir", "desc")

    allowed_sorts = {"quote_num", "name", "sales_rep", "customer_name", "date_created", "status"}
    if sort not in allowed_sorts:
        sort = "quote_num"
    if direction not in ("asc", "desc"):
        direction = "asc"

    queryset = Quote.objects.all()

    if status_filter != "all":
        queryset = queryset.filter(status=status_filter)

    if search_query:
        queryset = queryset.filter(
            Q(quote_num__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(category__icontains=search_query)
            | Q(customer_name__icontains=search_query)
            | Q(sales_rep__icontains=search_query)
        )

    order_field = f"-{sort}" if direction == "desc" else sort
    queryset = queryset.order_by(order_field)

    statuses = Quote.objects.values_list("status", flat=True).distinct().order_by("status")

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "quotes": page_obj,
        "search_query": search_query,
        "statuses": statuses,
        "selected_status": status_filter,
        "sort": sort,
        "dir": direction,
    }

    return render(request, "quotes.html", context)


@login_required
def create_quote(request):
    if request.method == "POST":
        form = CreateQuoteForm(request.POST, request.FILES)
        if form.is_valid():
            quote = form.save()
            messages.success(request, "Quote created successfully!")
            return redirect("view_quote", pk=quote.pk)
        else:
            messages.error(
                request,
                "There was an error creating the quote. Please check the form and try again.",
            )
    else:
        date_prefix = now().strftime("%m%d%y")
        last_quote = (
            Quote.objects.filter(quote_num__startswith=date_prefix)
            .order_by("-quote_num")
            .first()
        )
        if last_quote:
            last_suffix = int(last_quote.quote_num[-4:])
            new_suffix = f"{last_suffix + 1:02d}"
        else:
            new_suffix = "0001"
        auto_generated_quote_num = f"{date_prefix}{new_suffix}"

        initial = {"quote_num": auto_generated_quote_num}
        # Pre-populate customer/rep if coming from "New quote for same customer" button
        if request.GET.get("customer_name"):
            initial["customer_name"] = request.GET["customer_name"]
        if request.GET.get("sales_rep"):
            initial["sales_rep"] = request.GET["sales_rep"]

        form = CreateQuoteForm(initial=initial)

    hts_data = {h.pk: {"duty": float(h.duty_percent), "section301": float(h.section_301_percent), "extra": float(h.extra_tariff_percent), "total": float(h.total_percent)} for h in HtsCode.objects.all()}
    return render(request, "create_quote.html", {"form": form, "hts_data": json.dumps(hts_data)})


@login_required
def quote_pdf(request, quote_id):
    import urllib.request
    from weasyprint import HTML  # lazy import — avoids crash if system libs missing at startup

    quote = Quote.objects.get(id=quote_id)

    encoded_image = ""
    if quote.image:
        # Fetch image from Cloudinary (or local media) URL
        image_url = quote.image.url
        # If URL is relative (local dev), make it absolute
        if image_url.startswith("/"):
            image_url = request.build_absolute_uri(image_url)
        with urllib.request.urlopen(image_url) as resp:
            encoded_image = base64.b64encode(resp.read()).decode("utf-8")
    elif quote.image_url and not quote.image_url.startswith("http"):
        # Fallback: read from static/images/ for quotes not yet migrated
        image_path = os.path.join(settings.BASE_DIR, "static", "images", quote.image_url)
        if os.path.isfile(image_path):
            with open(image_path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read()).decode("utf-8")

    pdf_filename = f"{quote.display_name}.pdf"

    context = {"quote": quote, "encoded_image": encoded_image}

    html_string = render_to_string("quote_pdf.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{pdf_filename}"'

    HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(
        response, presentational_hints=True
    )

    return response
