import base64
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

from .forms import CreateQuoteForm
from .models import Quote


@login_required
def view_quote(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    return render(request, "view_quote.html", {"quote": quote})


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
    return render(request, "edit_quote.html", {"form": form, "quote": quote})


@login_required
def quotes(request):
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "Open")
    if not status_filter:
        status_filter = "Open"

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

    queryset = queryset.order_by("quote_num")

    statuses = Quote.objects.values_list("status", flat=True).distinct().order_by("status")

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "quotes": page_obj,
        "search_query": search_query,
        "statuses": statuses,
        "selected_status": status_filter,
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

        form = CreateQuoteForm(initial={"quote_num": auto_generated_quote_num})

    return render(request, "create_quote.html", {"form": form})


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
