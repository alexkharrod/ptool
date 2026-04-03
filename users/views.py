from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import redirect, render


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
            update_session_auth_hash(request, user)  # Keep them logged in
            return redirect("scouting_list" if user.scouting_only else "home")
    else:
        form = PasswordChangeForm(request.user)

    forced = getattr(request.user, "must_change_password", False)
    return render(request, "registration/change_password.html", {"form": form, "forced": forced})
