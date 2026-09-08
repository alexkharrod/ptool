import base64
import json

from users.decorators import section_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProspectForm
from .models import Prospect


def _active_show(request):
    """Return (show_name, show_date) from session, or ('', '')."""
    return (
        request.session.get("scouting_show_name", ""),
        request.session.get("scouting_show_date", ""),
    )


PAGE_SIZE = 24


@section_required("scouting")
def scouting_list(request):
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")   # "" = default (exclude Rejected), "all" = everything
    show_filter = request.GET.get("show", "")
    needs_details = request.GET.get("needs") == "1"

    queryset = Prospect.objects.all()

    if status_filter == "all":
        pass  # Show everything
    elif status_filter:
        queryset = queryset.filter(status=status_filter)
    else:
        queryset = queryset.exclude(status__in=["Rejected", "Adding"])  # default: active only

    if show_filter:
        queryset = queryset.filter(show_name__icontains=show_filter)

    if needs_details:
        queryset = queryset.filter(Prospect.needs_details_q()).exclude(promoted=True)

    if search_query:
        queryset = queryset.filter(
            Q(product_name__icontains=search_query)
            | Q(vendor_name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(show_name__icontains=search_query)
        )

    # Unique show names for filter dropdown
    shows = Prospect.objects.values_list("show_name", flat=True).distinct().order_by("show_name")

    paginator = Paginator(queryset, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Query string without `page`, so pagination links keep the current filters
    params = request.GET.copy()
    params.pop("page", None)
    base_qs = params.urlencode()

    active_show_name, active_show_date = _active_show(request)
    context = {
        "prospects": page_obj,
        "page_obj": page_obj,
        "total_count": paginator.count,
        "base_qs": base_qs,
        "search_query": search_query,
        "status_filter": status_filter,
        "show_filter": show_filter,
        "needs_details": needs_details,
        "shows": shows,
        "status_choices": Prospect.STATUS_CHOICES,
        "active_show_name": active_show_name,
        "active_show_date": active_show_date,
    }
    return render(request, "scouting_list.html", context)


@section_required("scouting")
def scouting_detail(request, pk):
    prospect = get_object_or_404(Prospect, pk=pk)
    return render(request, "scouting_detail.html", {"prospect": prospect})


@section_required("scouting")
def scouting_add(request):
    if request.method == "POST":
        form = ProspectForm(request.POST, request.FILES)
        is_async = request.headers.get("X-Async-Submit") == "1"
        if form.is_valid():
            prospect = form.save()
            if is_async:
                return JsonResponse({
                    "ok": True,
                    "pk": prospect.pk,
                    "prospect_number": prospect.prospect_number,
                    "product_name": prospect.product_name,
                    "vendor_name": prospect.vendor_name,
                })
            return redirect("scouting_detail", pk=prospect.pk)
        elif is_async:
            return JsonResponse({"ok": False, "errors": form.errors}, status=400)
    else:
        # Pre-populate from query params (same vendor flow or business card scan)
        initial = {}
        for field in ("show_name", "show_date", "vendor_name", "vendor_contact", "vendor_email", "vendor_website"):
            if request.GET.get(field):
                initial[field] = request.GET[field]
        # Pre-fill show from session if not already provided via query params
        if "show_name" not in initial:
            active_show_name, active_show_date = _active_show(request)
            if active_show_name:
                initial["show_name"] = active_show_name
                initial["show_date"] = active_show_date
        form = ProspectForm(initial=initial)
    active_show_name, active_show_date = _active_show(request)
    return render(request, "scouting_add.html", {
        "form": form,
        "active_show_name": active_show_name,
        "active_show_date": active_show_date,
    })


@section_required("scouting")
def scouting_edit(request, pk):
    prospect = get_object_or_404(Prospect, pk=pk)
    if request.method == "POST":
        form = ProspectForm(request.POST, request.FILES, instance=prospect)
        if form.is_valid():
            form.save()
            return redirect("scouting_detail", pk=prospect.pk)
    else:
        form = ProspectForm(instance=prospect)
    return render(request, "scouting_edit.html", {"form": form, "prospect": prospect})


@section_required("scouting")
def set_active_show(request):
    """Save the active show name/date to the session."""
    if request.method == "POST":
        show_name = request.POST.get("show_name", "").strip()
        show_date = request.POST.get("show_date", "").strip()
        if show_name:
            request.session["scouting_show_name"] = show_name
            request.session["scouting_show_date"] = show_date
        else:
            request.session.pop("scouting_show_name", None)
            request.session.pop("scouting_show_date", None)
    return redirect(request.POST.get("next", "scouting_list"))


@section_required("scouting")
def scouting_promote(request, pk):
    """Lean intermediate screen: pick Category + Vendor, auto-generate SKU, then create product stub."""
    import json as _json
    from products.models import Category, Product, Vendor

    prospect = get_object_or_404(Prospect, pk=pk)

    errors = []

    if request.method == "POST":
        sku = request.POST.get("sku", "").strip().upper()
        category_code = request.POST.get("category", "").strip()
        vendor_ref_id = request.POST.get("vendor_ref", "").strip()
        new_vendor_name = request.POST.get("new_vendor_name", "").strip()
        new_vendor_country = request.POST.get("new_vendor_country", "CN").strip()

        if not sku:
            errors.append("SKU is required.")
        elif Product.objects.filter(sku=sku).exists():
            errors.append(f"SKU '{sku}' already exists — please choose a different one.")

        # Validate new vendor name if that path was chosen
        if vendor_ref_id == "__new__" and not new_vendor_name:
            errors.append("Please enter a name for the new vendor.")

        if not errors:
            vendor_ref = None

            if vendor_ref_id == "__new__" and new_vendor_name:
                # Try case-insensitive exact match first to avoid true duplicates
                existing = Vendor.objects.filter(name__iexact=new_vendor_name).first()
                if existing:
                    vendor_ref = existing
                else:
                    vendor_ref = Vendor.objects.create(
                        name=new_vendor_name,
                        country=new_vendor_country,
                    )
            elif vendor_ref_id:
                try:
                    vendor_ref = Vendor.objects.get(pk=vendor_ref_id)
                except Vendor.DoesNotExist:
                    pass

            product = Product(
                sku=sku,
                name=prospect.product_name,
                category=category_code,
                vendor=prospect.vendor_name,
                vendor_ref=vendor_ref,
                description=prospect.description or "",
                colors=prospect.colors or "",
                production_time=prospect.lead_time or "",
                status="Open",
                source_show=prospect.show_name or "",
            )
            product.save()

            # Copy image from prospect to product
            if prospect.image:
                try:
                    import os
                    import urllib.request
                    from django.core.files.base import ContentFile
                    filename = os.path.basename(prospect.image.name) or "product.jpg"
                    with urllib.request.urlopen(prospect.image.url) as resp:
                        product.image.save(filename, ContentFile(resp.read()), save=True)
                except Exception:
                    pass  # Don't fail the promotion if image copy fails

            prospect.promoted = True
            prospect.promoted_sku = product.sku
            prospect.status = "Adding"
            prospect.save(update_fields=["promoted", "promoted_sku", "status"])
            return redirect("edit_product", pk=product.pk)

    categories = Category.objects.all()
    vendors = Vendor.objects.order_by("name")
    vendor_names_json = _json.dumps([v.name for v in vendors])

    return render(request, "scouting_promote.html", {
        "prospect": prospect,
        "categories": categories,
        "vendors": vendors,
        "vendor_names_json": vendor_names_json,
        "errors": errors,
        "posted": request.POST if errors else {},
    })


@section_required("scouting")
def update_prospect_status(request, pk):
    """AJAX POST — update a single prospect's status, return JSON."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)
    prospect = get_object_or_404(Prospect, pk=pk)
    data = json.loads(request.body)
    new_status = data.get("status")
    valid = [v for v, _ in Prospect.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)
    prospect.status = new_status
    prospect.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": prospect.status})


@section_required("scouting")
def bulk_update_prospects(request):
    """Bulk status update from the scouting list form."""
    if request.method == "POST":
        pks = request.POST.getlist("prospect_ids")
        new_status = request.POST.get("bulk_status")
        valid = [v for v, _ in Prospect.STATUS_CHOICES]
        if pks and new_status in valid:
            Prospect.objects.filter(pk__in=pks).update(status=new_status)
    return redirect(request.POST.get("next", "scouting_list"))


@section_required("scouting")
def scan_business_card(request):
    """Accepts a base64 image, calls Claude vision API, returns extracted vendor fields as JSON."""
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    try:
        import anthropic
        from django.conf import settings

        data = json.loads(request.body)
        image_b64 = data.get("image")
        media_type = data.get("media_type", "image/jpeg")

        if not image_b64:
            return JsonResponse({"ok": False, "error": "No image provided"}, status=400)

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "This is a vendor business card. Extract the following fields and return ONLY valid JSON, "
                                "no explanation:\n"
                                '{"vendor_name": "", "vendor_contact": "", "vendor_email": "", "vendor_website": ""}\n'
                                "Use empty string for any field not found on the card. "
                                "vendor_name is the company name, vendor_contact is the person's name."
                            ),
                        },
                    ],
                }
            ],
        )

        text = message.content[0].text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        extracted = json.loads(text)
        return JsonResponse({"ok": True, **extracted})

    except ImportError:
        return JsonResponse({"ok": False, "error": "Anthropic package not installed"}, status=500)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
