"""Rôles applicatifs (Groupes Django) — pas de rôle métier côté Oracle."""

ETUDIANT = 'Etudiant'
ENSEIGNANT = 'Enseignant'
SCOLARITE = 'Scolarite'
ADMIN_APP = 'Admin_application'  # Groupe Django (migration 0003)

ALL_ROLES = (ETUDIANT, ENSEIGNANT, SCOLARITE, ADMIN_APP)


def user_has_role(user, *role_names):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=role_names).exists()


def user_is_admin_app(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=ADMIN_APP).exists())
