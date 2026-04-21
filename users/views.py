import json

from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import CustomUser


def _staff_required(user):
    return user.is_authenticated and user.is_staff


# ─── Auth views ──────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def change_password(request):
    """Handles both forced first-login password change and voluntary changes."""
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
            update_session_auth_hash(request, user)
            return redirect("home")
    else:
        form = PasswordChangeForm(request.user)

    forced = getattr(request.user, "must_change_password", False)
    return render(request, "registration/change_password.html", {"form": form, "forced": forced})


# ─── User management (staff only) ────────────────────────────────────────────

@login_required
@user_passes_test(_staff_required)
def user_manage(request):
    """List all users with access toggle checkboxes."""
    users = CustomUser.objects.all().order_by("first_name", "last_name", "email")
    return render(request, "users/user_manage.html", {"users": users})


@login_required
@user_passes_test(_staff_required)
@require_POST
def user_toggle_access(request, pk):
    """AJAX: toggle a single access flag for a user."""
    user = get_object_or_404(CustomUser, pk=pk)
    try:
        data = json.loads(request.body)
        field = data.get("field")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"ok": False, "error": "Invalid request"}, status=400)

    allowed_fields = {"access_products", "access_quotes", "access_scouting",
                      "access_shipments", "access_shipments_logistics", "is_active"}
    if field not in allowed_fields:
        return JsonResponse({"ok": False, "error": "Invalid field"}, status=400)

    current = getattr(user, field)
    setattr(user, field, not current)
    user.save(update_fields=[field])
    return JsonResponse({"ok": True, "value": getattr(user, field)})


@login_required
@user_passes_test(_staff_required)
def user_create(request):
    """Create a new user with an initial temporary password."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "").strip()
        access_products             = "access_products"             in request.POST
        access_quotes               = "access_quotes"               in request.POST
        access_scouting             = "access_scouting"             in request.POST
        access_shipments            = "access_shipments"            in request.POST
        access_shipments_logistics  = "access_shipments_logistics"  in request.POST

        if not email or not first_name or not last_name or not password:
            messages.error(request, "All fields are required.")
            return render(request, "users/user_create.html", {"post": request.POST})

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, f"A user with email {email} already exists.")
            return render(request, "users/user_create.html", {"post": request.POST})

        # Validate password against site rules before hitting the DB
        try:
            validate_password(password)
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
            return render(request, "users/user_create.html", {"post": request.POST})

        try:
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                access_products=access_products,
                access_quotes=access_quotes,
                access_scouting=access_scouting,
                access_shipments=access_shipments,
                access_shipments_logistics=access_shipments_logistics,
                must_change_password=True,
            )
        except Exception as e:
            messages.error(request, f"Could not create user: {e}")
            return render(request, "users/user_create.html", {"post": request.POST})

        messages.success(request, f"User {user.get_full_name()} created. They'll be prompted to set a new password on first login.")
        return redirect("user_manage")

    return render(request, "users/user_create.html", {"post": {}})


@login_required
@user_passes_test(_staff_required)
def user_edit(request, pk):
    """Edit a user's details and access flags."""
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "reset_password":
            new_pw = request.POST.get("new_password", "").strip()
            if not new_pw:
                messages.error(request, "Password cannot be empty.")
            else:
                user.set_password(new_pw)
                user.must_change_password = True
                user.save(update_fields=["password", "must_change_password"])
                messages.success(request, f"Password reset for {user.get_full_name()}. They'll be prompted to change it on next login.")
            return redirect("user_edit", pk=pk)

        # Regular edit
        user.first_name                    = request.POST.get("first_name", user.first_name).strip()
        user.last_name                     = request.POST.get("last_name",  user.last_name).strip()
        user.access_products               = "access_products"               in request.POST
        user.access_quotes                 = "access_quotes"                 in request.POST
        user.access_scouting               = "access_scouting"               in request.POST
        user.access_shipments              = "access_shipments"              in request.POST
        user.access_shipments_logistics    = "access_shipments_logistics"    in request.POST
        user.is_active                     = "is_active"                     in request.POST
        user.save(update_fields=["first_name", "last_name", "access_products",
                                  "access_quotes", "access_scouting",
                                  "access_shipments", "access_shipments_logistics",
                                  "is_active"])
        messages.success(request, "User updated.")
        return redirect("user_manage")

    return render(request, "users/user_edit.html", {"edited_user": user})
