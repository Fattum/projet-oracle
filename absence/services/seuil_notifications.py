"""
Pousse les alertes HISTORIQUE_ALERTE (seuil Oracle/SQLite) vers NotificationApp
pour que l'étudiant les voie dans « Notifications ».
Idempotent : une ligne par id d'alerte (marqueur dans le corps).
"""

from absence.models import NotificationApp


def _marker_alerte(pk):
    return f"<!--alerte-seuil:{pk}-->"


def synchroniser_notifications_seuil_etudiant(user, alertes):
    """
    Pour chaque HistoriqueAlerte, crée une notification lue=False si absente.
    `alertes` : itérable d'instances HistoriqueAlerte (avec id_cours, id_annee chargés).
    """
    if not alertes or not user or not user.is_authenticated:
        return
    for al in alertes:
        m = _marker_alerte(al.pk)
        if NotificationApp.objects.filter(user=user, corps__contains=m).exists():
            continue
        cours = getattr(al, "id_cours", None)
        annee = getattr(al, "id_annee", None)
        code = getattr(cours, "code_cours", None) or "cours"
        lib_annee = getattr(annee, "libelle", None) or ""
        titre = f"Seuil d'absences — {code}"
        if lib_annee:
            titre = f"{titre} ({lib_annee})"
        msg = (al.message or "").strip()
        corps = (
            f"Vous avez atteint le seuil d'absences non justifiées pour ce cours "
            f"({al.nb_abs_non_just} enregistrée(s)).\n\n{msg}\n{m}"
        )
        NotificationApp.objects.create(
            user=user,
            titre=titre[:200],
            corps=corps[:4000],
            lu=False,
        )


def corps_notification_sans_marqueur(corps):
    """Retire le marqueur technique de dédoublonnage pour l'affichage."""
    if not corps:
        return ''
    idx = corps.find('<!--alerte-seuil:')
    if idx >= 0:
        return corps[:idx].rstrip()
    return corps
