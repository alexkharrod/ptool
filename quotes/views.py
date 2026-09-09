import json
import os

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.timezone import now

from products.models import Product
from users.decorators import section_required
from .models import CustomerQuote, QuoteLineItem, QuotePriceTier, SalesRep


# The original single-product `Quote` system was retired in September 2026.
# Its model/table and Django-admin registration remain (read-only history);
# `manage.py export_legacy_quotes` renders those records to PDF.

@section_required("quotes")
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


@section_required("quotes")
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


@section_required("quotes")
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


@section_required("quotes")
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


@section_required("quotes")
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


@section_required("quotes")
def cq_item_delete(request, item_pk):
    """AJAX: delete a line item."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    item = get_object_or_404(QuoteLineItem, pk=item_pk)
    item.delete()
    return JsonResponse({'ok': True})


@section_required("quotes")
def cq_delete(request, pk):
    """Delete an entire quote and redirect to the list."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    cq = get_object_or_404(CustomerQuote, pk=pk)
    cq.delete()
    return JsonResponse({'ok': True})


@section_required("quotes")
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


@section_required("quotes")
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


@section_required("quotes")
def cq_view(request, pk):
    """Read-only view of a quote with download PDF button."""
    cq = get_object_or_404(CustomerQuote, pk=pk)
    items = cq.line_items.select_related('product__hts_code').prefetch_related('tiers', 'product__imprint_methods')
    return render(request, 'cq/cq_view.html', {'cq': cq, 'items': items})


@section_required("quotes")
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
