from django.db.utils import OperationalError

from . import roles


def app_nav(request):
    ctx = {
        'role_etudiant': False,
        'role_enseignant': False,
        'role_scolarite': False,
        'role_admin_app': False,
        'role_labels': [],
        'has_any_app_role': False,
        'notif_non_lues': 0,
        'nav_display_name': '',
    }
    u = request.user
    if not u.is_authenticated:
        return ctx
    ctx['role_etudiant'] = roles.user_has_role(u, roles.ETUDIANT)
    ctx['role_enseignant'] = roles.user_has_role(u, roles.ENSEIGNANT)
    ctx['role_scolarite'] = roles.user_has_role(u, roles.SCOLARITE)
    ctx['role_admin_app'] = roles.user_is_admin_app(u)

    labels = []
    if ctx['role_etudiant']:
        labels.append('Étudiant')
    if ctx['role_enseignant']:
        labels.append('Enseignant')
    if ctx['role_scolarite']:
        labels.append('Scolarité')
    if ctx['role_admin_app']:
        labels.append('Admin application')
    ctx['role_labels'] = labels
    ctx['has_any_app_role'] = bool(labels) or u.is_superuser
    ctx['nav_display_name'] = u.get_username()

    try:
        from .models import NotificationApp, ProfilApp

        ctx['notif_non_lues'] = NotificationApp.objects.filter(user=u, lu=False).count()
        pa = ProfilApp.objects.filter(user=u).only('nom_affiche').first()
        if pa:
            nom = (pa.nom_affiche or '').strip()
            if nom:
                ctx['nav_display_name'] = nom
    except OperationalError:
        pass
    return ctx
