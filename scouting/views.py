import base64
import json

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from products.forms import CreateProductForm
from .forms import ProspectForm
from .models import Prospect


@login_required
def scouting_list(request):
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "")   # "" = default (exclude Rejected), "all" = everything
    show_filter = request.GET.get("show", "")

    queryset = Prospect.objects.all()

    if status_filter == "all":
        pass  # Show everything including Rejected
    elif status_filter:
        queryset = queryset.filter(status=status_filter)
    else:
        queryset = queryset.exclude(status="Rejected")

    if show_filter:
        queryset = queryset.filter(show_name__icontains=show_filter)

    if search_query:
        queryset = queryset.filter(
            Q(product_name__icontains=search_query)
            | Q(vendor_name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(show_name__icontains=search_query)
        )

    # Unique show names for filter dropdown
    shows = Prospect.objects.values_list("show_name", flat=True).distinct().order_by("show_name")

    context = {
        "prospects": queryset,
        "search_query": search_query,
        "status_filter": status_filter,
        "show_filter": show_filter,
        "shows": shows,
        "status_choices": Prospect.STATUS_CHOICES,
    }
    return render(request, "scouting_list.html", context)


@login_required
def scouting_detail(request, pk):
    prospect = get_object_or_404(Prospect, pk=pk)
    return render(request, "scouting_detail.html", {"prospect": prospect})


@login_required
def scouting_add(request):
    if request.method == "POST":
        form = ProspectForm(request.POST, request.FILES)
        is_async = request.headers.get("X-Async-Submit") == "1"
        if form.is_valid():
            prospect = form.save()
            if is_async:
                from django.http import JsonResponse as JR
                return JR({"ok": True, "pk": prospect.pk})
            return redirect("scouting_detail", pk=prospect.pk)
        elif is_async:
            from django.http import JsonResponse as JR
            return JR({"ok": False, "errors": form.errors}, status=400)
    else:
        # Pre-populate from query params (same vendor flow or business card scan)
        initial = {}
        for field in ("show_name", "show_date", "vendor_name", "vendor_contact", "vendor_email", "vendor_website"):
            if request.GET.get(field):
                initial[field] = request.GET[field]
        form = ProspectForm(initial=initial)
    return render(request, "scouting_add.html", {"form": form})


@login_required
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


@login_required
def scouting_promote(request, pk):
    """Pre-fills the Add Product form with scouting data."""
    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == "POST":
        form = CreateProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            # Mark prospect as promoted
            prospect.promoted = True
            prospect.promoted_sku = product.sku
            prospect.status = "Adding"
            prospect.save(update_fields=["promoted", "promoted_sku", "status"])
            return redirect("view_product", pk=product.pk)
    else:
        # Map scouting fields → product fields
        initial = {
            "name": prospect.product_name,
            "vendor": prospect.vendor_name,
            "description": prospect.description,
            "colors": prospect.colors,
            "production_time": prospect.lead_time,
            "status": "Open",
        }
        form = CreateProductForm(initial=initial)

    return render(
        request,
        "scouting_promote.html",
        {"form": form, "prospect": prospect},
    )


@login_required
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


@login_required
def bulk_update_prospects(request):
    """Bulk status update from the scouting list form."""
    if request.method == "POST":
        pks = request.POST.getlist("prospect_ids")
        new_status = request.POST.get("bulk_status")
        valid = [v for v, _ in Prospect.STATUS_CHOICES]
        if pks and new_status in valid:
            Prospect.objects.filter(pk__in=pks).update(status=new_status)
    return redirect(request.POST.get("next", "scouting_list"))


@login_required
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
