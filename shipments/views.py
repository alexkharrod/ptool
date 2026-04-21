from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ShipmentDocumentForm, ShipmentForm, ShipmentItemFormSet
from .models import Shipment, ShipmentDocument, ShipmentItem


def _can_access(user):
    return user.is_staff or getattr(user, "access_shipments", False)


@login_required
def shipment_list(request):
    if not _can_access(request.user):
        return redirect("home")

    search = request.GET.get("search", "")
    mode_filter = request.GET.get("mode", "")
    status_filter = request.GET.get("status", "")
    show_closed = request.GET.get("show_closed", "")

    qs = Shipment.objects.prefetch_related("items")

    if not show_closed:
        qs = qs.exclude(status__in=["Delivered", "Cancelled"])

    if mode_filter:
        qs = qs.filter(mode=mode_filter)

    if status_filter:
        qs = qs.filter(status=status_filter)

    if search:
        qs = qs.filter(
            Q(ags_number__icontains=search)
            | Q(po_numbers__icontains=search)
            | Q(carrier__icontains=search)
            | Q(vessel__icontains=search)
            | Q(tracking_number__icontains=search)
            | Q(notes__icontains=search)
            | Q(items__sku__icontains=search)
            | Q(items__description__icontains=search)
            | Q(items__po_number__icontains=search)
        ).distinct()

    context = {
        "shipments": qs,
        "search": search,
        "mode_filter": mode_filter,
        "status_filter": status_filter,
        "show_closed": show_closed,
        "mode_choices": Shipment.MODE_CHOICES,
        "status_choices": Shipment.STATUS_CHOICES,
    }
    return render(request, "shipments/shipment_list.html", context)


@login_required
def shipment_detail(request, pk):
    if not _can_access(request.user):
        return redirect("home")
    shipment = get_object_or_404(Shipment, pk=pk)
    doc_form = ShipmentDocumentForm()
    return render(request, "shipments/shipment_detail.html", {
        "shipment": shipment,
        "doc_form": doc_form,
    })


@login_required
def shipment_add(request):
    if not _can_access(request.user):
        return redirect("home")

    if request.method == "POST":
        form = ShipmentForm(request.POST)
        formset = ShipmentItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            shipment = form.save()
            formset.instance = shipment
            formset.save()
            return redirect("shipment_detail", pk=shipment.pk)
    else:
        next_num = Shipment.next_shipment_number()
        form = ShipmentForm(initial={"shipment_number": next_num})
        formset = ShipmentItemFormSet()

    return render(request, "shipments/shipment_add.html", {
        "form": form,
        "formset": formset,
    })


@login_required
def shipment_edit(request, pk):
    if not _can_access(request.user):
        return redirect("home")

    shipment = get_object_or_404(Shipment, pk=pk)

    if request.method == "POST":
        form = ShipmentForm(request.POST, instance=shipment)
        formset = ShipmentItemFormSet(request.POST, instance=shipment)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("shipment_detail", pk=shipment.pk)
    else:
        form = ShipmentForm(instance=shipment)
        formset = ShipmentItemFormSet(instance=shipment)

    return render(request, "shipments/shipment_edit.html", {
        "form": form,
        "formset": formset,
        "shipment": shipment,
    })


@login_required
def shipment_upload_doc(request, pk):
    """AJAX or form POST — attach a document to a shipment."""
    if not _can_access(request.user):
        return redirect("home")

    shipment = get_object_or_404(Shipment, pk=pk)

    if request.method == "POST":
        form = ShipmentDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.shipment = shipment
            doc.save()
    return redirect("shipment_detail", pk=shipment.pk)


@login_required
def shipment_delete_doc(request, pk, doc_pk):
    if not _can_access(request.user):
        return redirect("home")
    doc = get_object_or_404(ShipmentDocument, pk=doc_pk, shipment__pk=pk)
    if request.method == "POST":
        doc.delete()
    return redirect("shipment_detail", pk=pk)


@login_required
def shipment_parse_doc(request):
    """
    AJAX POST — accepts an uploaded XLS/XLSX packing list / CI file and returns
    parsed shipment items as JSON so the add/edit form can be pre-populated.
    """
    if not _can_access(request.user):
        return JsonResponse({"ok": False, "error": "Access denied"}, status=403)
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    uploaded = request.FILES.get("file")
    if not uploaded:
        return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)

    from .parse_doc import parse_shipment_doc
    result = parse_shipment_doc(uploaded)
    return JsonResponse({"ok": True, **result})


@login_required
def shipment_update_status(request, pk):
    """AJAX POST — quick status update from the list view."""
    if not _can_access(request.user):
        return JsonResponse({"ok": False, "error": "Access denied"}, status=403)

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    import json
    shipment = get_object_or_404(Shipment, pk=pk)
    data = json.loads(request.body)
    new_status = data.get("status")
    valid = [v for v, _ in Shipment.STATUS_CHOICES]
    if new_status not in valid:
        return JsonResponse({"ok": False, "error": "Invalid status"}, status=400)

    shipment.status = new_status
    shipment.save(update_fields=["status"])
    return JsonResponse({"ok": True, "status": shipment.status})
