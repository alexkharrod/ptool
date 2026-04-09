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

from products.models import HtsCode, Product
from .forms import CreateQuoteForm
from .models import Quote, CustomerQuote, QuoteLineItem, QuotePriceTier, SalesRep


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


# ═══════════════════════════════════════════════════════════════════════════════
#  NEW QUOTE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

@login_required
def cq_list(request):
    """List all customer quotes."""
    quotes = CustomerQuote.objects.select_related('rep').prefetch_related('line_items')
    status = request.GET.get('status', '')
    if status:
        quotes = quotes.filter(status=status)
    search = request.GET.get('q', '').strip()
    if search:
        quotes = quotes.filter(customer_name__icontains=search)
    return render(request, 'cq/cq_list.html', {
        'quotes': quotes,
        'status_filter': status,
        'search': search,
        'status_choices': CustomerQuote.STATUS_CHOICES,
    })


@login_required
def cq_create(request):
    """Create a new customer quote (header only; items added on edit page)."""
    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', '').strip()
        rep_id = request.POST.get('rep', '').strip()
        date = request.POST.get('date', '').strip()
        notes = request.POST.get('notes', '').strip()
        status = request.POST.get('status', 'draft').strip()

        if not customer_name:
            return render(request, 'cq/cq_create.html', {
                'error': 'Customer name is required.',
                'reps': SalesRep.objects.all(),
                'posted': request.POST,
            })

        cq = CustomerQuote(
            customer_name=customer_name,
            notes=notes,
            status=status,
        )
        if date:
            cq.date = date
        if rep_id:
            try:
                cq.rep = SalesRep.objects.get(pk=rep_id)
            except SalesRep.DoesNotExist:
                pass
        cq.save()
        return redirect('cq_edit', pk=cq.pk)

    return render(request, 'cq/cq_create.html', {
        'reps': SalesRep.objects.all(),
        'today': now().date(),
    })


@login_required
def cq_edit(request, pk):
    """Edit quote header + manage line items."""
    cq = get_object_or_404(CustomerQuote, pk=pk)

    if request.method == 'POST' and request.POST.get('_action') == 'save_header':
        cq.customer_name = request.POST.get('customer_name', cq.customer_name).strip()
        rep_id = request.POST.get('rep', '')
        if rep_id:
            try:
                cq.rep = SalesRep.objects.get(pk=rep_id)
            except SalesRep.DoesNotExist:
                pass
        else:
            cq.rep = None
        date_val = request.POST.get('date', '')
        if date_val:
            cq.date = date_val
        cq.notes = request.POST.get('notes', '').strip()
        cq.status = request.POST.get('status', cq.status)
        cq.save()
        return redirect('cq_edit', pk=cq.pk)

    items = cq.line_items.select_related('product__hts_code').prefetch_related('tiers', 'product__imprint_methods')
    return render(request, 'cq/cq_edit.html', {
        'cq': cq,
        'items': items,
        'reps': SalesRep.objects.all(),
        'status_choices': CustomerQuote.STATUS_CHOICES,
    })


@login_required
def cq_item_add(request, quote_pk):
    """AJAX: add a line item to a quote from a product SKU. Returns rendered item card HTML."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    cq = get_object_or_404(CustomerQuote, pk=quote_pk)
    data = json.loads(request.body)
    product_pk = data.get('product_pk')

    try:
        product = Product.objects.get(pk=product_pk)
    except Product.DoesNotExist:
        from django.http import JsonResponse
        return JsonResponse({'ok': False, 'error': 'Product not found'}, status=404)

    # Next sort order
    last = cq.line_items.order_by('-sort_order').values_list('sort_order', flat=True).first()
    sort = (last or 0) + 1

    # Default imprint method: first from product's methods, or free-text field
    methods = list(product.imprint_methods.values_list('name', flat=True))
    default_method = methods[0] if methods else (product.imprint_method or '')

    item = QuoteLineItem.objects.create(
        quote=cq,
        product=product,
        sort_order=sort,
        imprint_method=default_method,
        setup_charge=0,
    )
    # Create 3 blank tiers by default
    for t in range(1, 4):
        QuotePriceTier.objects.create(line_item=item, tier_number=t)

    # Assign quote number on first item add (MMDD-AH-SKU-NN)
    if not cq.quote_number:
        rep_initials = cq.rep.initials if cq.rep else None
        cq.quote_number = CustomerQuote._next_quote_number(
            date=cq.date,
            rep_initials=rep_initials,
            sku=product.sku,
        )
        cq.save(update_fields=['quote_number'])

    from django.http import JsonResponse
    return JsonResponse({'ok': True, 'item_pk': item.pk, 'quote_number': cq.quote_number})


@login_required
def cq_item_save(request, item_pk):
    """AJAX: save edits to a single line item and its price tiers."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)

    item = get_object_or_404(QuoteLineItem, pk=item_pk)
    data = json.loads(request.body)

    item.imprint_method   = data.get('imprint_method', item.imprint_method)
    item.setup_charge     = data.get('setup_charge') or 0
    item.run_charge       = data.get('run_charge') or None
    item.our_air_freight  = data.get('our_air_freight') or None
    item.our_ocean_freight= data.get('our_ocean_freight') or None
    item.notes            = data.get('notes', '')
    item.save()

    # Upsert tiers
    for t_data in data.get('tiers', []):
        tier_num = int(t_data.get('tier_number', 0))
        if not tier_num:
            continue
        tier, _ = QuotePriceTier.objects.get_or_create(line_item=item, tier_number=tier_num)
        tier.quantity        = t_data.get('quantity') or 0
        tier.unit_price      = t_data.get('unit_price') or 0
        tier.air_total       = t_data.get('air_total') or None
        tier.ocean_total     = t_data.get('ocean_total') or None
        tier.air_lead_time   = t_data.get('air_lead_time', '')
        tier.ocean_lead_time = t_data.get('ocean_lead_time', '')
        tier.save()

    # Remove tiers that were deleted (tier_number not in the posted list)
    posted_tier_nums = {int(t.get('tier_number', 0)) for t in data.get('tiers', []) if t.get('tier_number')}
    item.tiers.exclude(tier_number__in=posted_tier_nums).delete()

    return JsonResponse({'ok': True})


@login_required
def cq_item_delete(request, item_pk):
    """AJAX: delete a line item."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    item = get_object_or_404(QuoteLineItem, pk=item_pk)
    item.delete()
    return JsonResponse({'ok': True})


@login_required
def cq_rep_add(request):
    """AJAX: create a new sales rep. Returns {ok, pk, name}."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    data = json.loads(request.body)
    name     = data.get('name', '').strip()
    initials = data.get('initials', '').strip().upper()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Name required'}, status=400)
    existing = SalesRep.objects.filter(name__iexact=name).first()
    if existing:
        return JsonResponse({'ok': True, 'pk': existing.pk, 'name': str(existing), 'created': False})
    rep = SalesRep.objects.create(name=name, initials=initials)
    return JsonResponse({'ok': True, 'pk': rep.pk, 'name': str(rep), 'created': True})


@login_required
def cq_product_search(request):
    """AJAX: search products by SKU or name for the item picker."""
    from django.http import JsonResponse
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    qs = Product.objects.filter(
        Q(sku__icontains=q) | Q(name__icontains=q)
    ).exclude(status='Canceled').order_by('sku')[:20]
    results = []
    for p in qs:
        results.append({
            'pk': p.pk,
            'sku': p.sku,
            'name': p.name or '',
            'image_url': p.image.url if p.image else (p.image_url or ''),
            'imprint_methods': list(p.imprint_methods.values_list('name', flat=True)),
            'imprint_method': p.imprint_method or '',
            'setup_charge': 0,
        })
    return JsonResponse({'results': results})


@login_required
def cq_view(request, pk):
    """Read-only view of a quote with download PDF button."""
    cq = get_object_or_404(CustomerQuote, pk=pk)
    items = cq.line_items.select_related('product__hts_code').prefetch_related('tiers', 'product__imprint_methods')
    return render(request, 'cq/cq_view.html', {'cq': cq, 'items': items})


@login_required
def cq_pdf(request, pk):
    """Generate and download the quote PDF."""
    from weasyprint import HTML as WP_HTML
    cq = get_object_or_404(CustomerQuote, pk=pk)
    items = list(cq.line_items.select_related('product__hts_code').prefetch_related('tiers', 'product__imprint_methods'))

    # Embed logo as base64 for reliable WeasyPrint rendering
    logo_b64 = ""
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "LI-Circle.png")
    if os.path.isfile(logo_path):
        import base64 as _b64
        with open(logo_path, "rb") as lf:
            logo_b64 = _b64.b64encode(lf.read()).decode("utf-8")

    # Mark as sent when PDF is downloaded
    if cq.status == 'draft':
        cq.status = 'sent'
        cq.save(update_fields=['status'])

    html_string = render_to_string('cq/cq_pdf.html', {
        'cq': cq,
        'items': items,
        'request': request,
        'logo_b64': logo_b64,
    })

    response = HttpResponse(content_type='application/pdf')
    safe_customer = cq.customer_name.replace(' ', '_').replace('/', '-')[:30]
    response['Content-Disposition'] = f'attachment; filename="{cq.quote_number}_{safe_customer}.pdf"'
    WP_HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf(response, presentational_hints=True)
    return response
