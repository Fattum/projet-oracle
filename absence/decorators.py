from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from . import roles


def role_required(*group_names):
    """Accès réservé aux groupes listés (ou superuser)."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)
            messages.error(
                request,
                'Cette page n’est pas accessible avec votre compte. Connectez-vous avec un autre utilisateur de démo.',
            )
            return redirect('dashboard')

        return _wrapped

    return decorator


def etudiant_ou_staff(view_func):
    """Étudiant (groupe) ou scolarité / enseignant / admin app pour zones élargies."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if roles.user_has_role(
            request.user,
            roles.ETUDIANT,
            roles.ENSEIGNANT,
            roles.SCOLARITE,
            roles.ADMIN_APP,
        ) or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        messages.error(request, 'Accès réservé aux comptes de l’application.')
        return redirect('login')

    return _wrapped
