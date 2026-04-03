"""
Sur SQLite, les triggers Oracle des quotas n’existent pas : on reproduit ici
la règle « alerte au moment où le nombre d’absences non justifiées atteint le seuil »
pour pouvoir tester l’écran Alertes en local.
Sur Oracle, la base gère déjà les alertes : on ne fait rien.
"""

from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    Absence,
    HistoriqueAlerte,
    Inscription,
    ParamCoursSeuil,
    ParamGlobalAnnee,
    ProfilEtudiant,
)
from .services.seuil_notifications import synchroniser_notifications_seuil_etudiant


def _seuil_non_justif(cours_id, annee_id):
    try:
        return ParamCoursSeuil.objects.get(
            id_cours_id=cours_id,
            id_annee_id=annee_id,
        ).seuil_non_justif
    except ParamCoursSeuil.DoesNotExist:
        pass
    try:
        return ParamGlobalAnnee.objects.get(id_annee_id=annee_id).seuil_non_justif
    except ParamGlobalAnnee.DoesNotExist:
        pass
    return 3


def _count_non_just(etu_id, cours_id, annee_id):
    return Absence.objects.filter(
        justifiee='N',
        id_inscription__statut_insc='VALIDEE',
        id_inscription__id_etudiant_id=etu_id,
        id_inscription__id_cours_id=cours_id,
        id_inscription__id_annee_id=annee_id,
    ).count()


@receiver(post_save, sender=Absence)
def creer_alerte_si_seuil_sqlite(sender, instance, created, **kwargs):
    if connection.vendor != 'sqlite':
        return
    if not created:
        return
    if instance.justifiee != 'N':
        return

    ins = Inscription.objects.select_related(
        'id_etudiant',
        'id_cours',
        'id_annee',
    ).get(pk=instance.id_inscription_id)
    etu_id = ins.id_etudiant_id
    cours_id = ins.id_cours_id
    annee_id = ins.id_annee_id

    seuil = _seuil_non_justif(cours_id, annee_id)
    cnt = _count_non_just(etu_id, cours_id, annee_id)
    prev = cnt - 1

    if cnt < seuil or prev >= seuil:
        return

    code = ins.id_cours.code_cours
    msg = (
        f'Quota atteint : {cnt} absence(s) non justifiée(s) (seuil {seuil}) '
        f'pour le cours {code} / année {ins.id_annee.libelle}'
    )
    HistoriqueAlerte.objects.create(
        id_etudiant_id=etu_id,
        id_cours_id=cours_id,
        id_annee_id=annee_id,
        nb_abs_non_just=cnt,
        date_alerte=timezone.now(),
        message=msg[:500],
    )
    try:
        pe = ProfilEtudiant.objects.get(etudiant_id=etu_id)
        al = (
            HistoriqueAlerte.objects.select_related('id_cours', 'id_annee')
            .filter(id_etudiant_id=etu_id, id_cours_id=cours_id, id_annee_id=annee_id)
            .order_by('-date_alerte')
            .first()
        )
        if al:
            synchroniser_notifications_seuil_etudiant(pe.user, [al])
    except ProfilEtudiant.DoesNotExist:
        pass
