"""
Pousse les alertes HISTORIQUE_ALERTE (seuil Oracle/SQLite) vers NotificationApp
pour que l'étudiant les voie dans « Notifications ».
Idempotent : une ligne par id d'alerte (marqueur dans le corps).

E-mails : envoyés une fois par alerte (table SeuilAlerteEmailEnvoye), indépendamment
de la notification in-app (sinon pas d'e-mail si la notif existait déjà).
"""

from absence.models import NotificationApp, SeuilAlerteEmailEnvoye

from .seuil_email import envoyer_emails_alerte_seuil


def _marker_alerte(pk):
    return f"<!--alerte-seuil:{pk}-->"


def _titre_et_corps_pour_alerte(al):
    cours = getattr(al, "id_cours", None)
    annee = getattr(al, "id_annee", None)
    code = getattr(cours, "code_cours", None) or "cours"
    lib_annee = getattr(annee, "libelle", None) or ""
    titre = f"Seuil d'absences — {code}"
    if lib_annee:
        titre = f"{titre} ({lib_annee})"
    msg = (al.message or "").strip()
    corps_affiche = (
        f"Vous avez atteint le seuil d'absences non justifiées pour ce cours "
        f"({al.nb_abs_non_just} enregistrée(s)).\n\n{msg}"
    )
    return titre[:200], corps_affiche[:4000]


def synchroniser_notifications_seuil_etudiant(user, alertes):
    """
    Pour chaque HistoriqueAlerte, crée une notification lue=False si absente.
    Envoie l'e-mail seuil une fois par alerte (même si la notif existait déjà).
    `alertes` : itérable d'instances HistoriqueAlerte (avec id_cours, id_annee, id_etudiant).
    """
    if not alertes or not user or not user.is_authenticated:
        return
    for al in alertes:
        m = _marker_alerte(al.pk)
        titre, corps_affiche = _titre_et_corps_pour_alerte(al)
        etu = getattr(al, "id_etudiant", None)

        if not NotificationApp.objects.filter(user=user, corps__contains=m).exists():
            corps = f"{corps_affiche}\n{m}"
            NotificationApp.objects.create(
                user=user,
                titre=titre,
                corps=corps[:4000],
                lu=False,
            )

        if not SeuilAlerteEmailEnvoye.objects.filter(
            historique_alerte_id=al.pk
        ).exists():
            if envoyer_emails_alerte_seuil(titre, corps_affiche, etudiant=etu):
                SeuilAlerteEmailEnvoye.objects.create(
                    historique_alerte_id=al.pk
                )


def corps_notification_sans_marqueur(corps):
    """Retire le marqueur technique de dédoublonnage pour l'affichage."""
    if not corps:
        return ''
    idx = corps.find('<!--alerte-seuil:')
    if idx >= 0:
        return corps[:idx].rstrip()
    return corps
