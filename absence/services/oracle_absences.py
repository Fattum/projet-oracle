"""
Enregistrement d’absence : Oracle → package PKG_GESTION_ABSENCES (transaction).
SQLite → ORM (même schéma local, sans triggers Oracle).
"""

from django.db import connection, transaction
from django.db.utils import DatabaseError
from django.utils import timezone

from absence.models import Absence


def _oracle_var_for_callproc(out_var):
    """
    Django enveloppe cursor.var() (VariableWrapper). execute() gère ce type ;
    oracledb.callproc exige l'objet var interne → DPY-3002 si on passe le wrapper.
    """
    bind = getattr(out_var, "bind_parameter", None)
    return bind(None) if bind else out_var


def enregistrer_absence_transaction(
    id_inscription,
    id_seance,
    motif,
    justifiee,
):
    """
    Retourne l’identifiant de l’absence créée.
    Lève DatabaseError / ValueError en cas d’échec (contraintes Oracle, package).
    """
    j = (justifiee or 'N').strip().upper()[:1]
    if j not in ('O', 'N'):
        raise ValueError('Justification invalide (O ou N).')

    motif = (motif or '').strip()[:300]

    with transaction.atomic():
        if connection.vendor == 'oracle':
            with connection.cursor() as cursor:
                out = cursor.var(int)
                cursor.callproc(
                    'PKG_GESTION_ABSENCES.P_ENREGISTRER_ABSENCE',
                    [
                        int(id_inscription),
                        int(id_seance),
                        motif,
                        j,
                        _oracle_var_for_callproc(out),
                    ],
                )
                pk = out.getvalue()
                if pk is None:
                    raise DatabaseError(
                        'La procédure Oracle n’a pas retourné d’identifiant d’absence.'
                    )
                return int(pk)
        a = Absence.objects.create(
            id_inscription_id=int(id_inscription),
            id_seance_id=int(id_seance),
            motif=motif or None,
            justifiee=j,
            date_saisie=timezone.now(),
        )
        return a.pk


def maj_justification_absence(id_absence, justifiee, motif):
    """
    Mise à jour justification / motif (scolarité). Oracle : package ;
    SQLite : ORM dans une transaction.
    """
    from django.db import connection, transaction

    j = (justifiee or 'N').strip().upper()[:1]
    if j not in ('O', 'N'):
        raise ValueError('Justification invalide (O ou N).')
    motif = (motif or '').strip()[:300]

    with transaction.atomic():
        if connection.vendor == 'oracle':
            with connection.cursor() as cursor:
                cursor.callproc(
                    'PKG_GESTION_ABSENCES.P_MAJ_ABSENCE_JUSTIF',
                    [int(id_absence), j, motif],
                )
            return
        updated = Absence.objects.filter(pk=int(id_absence)).update(
            justifiee=j,
            motif=motif or None,
        )
        if not updated:
            raise ValueError('Absence introuvable.')


def notifier_scolarite_nouvelle_absence(cours_label, etudiant_label):
    """Notifications applicatives Django (table gérée par Django, pas Oracle)."""
    from django.contrib.auth.models import User

    from absence import roles
    from absence.models import NotificationApp

    titre = 'Nouvelle absence enregistrée'
    corps = f'Cours {cours_label} — Étudiant {etudiant_label}'
    groupes = [roles.SCOLARITE, roles.ADMIN_APP]
    for u in User.objects.filter(groups__name__in=groupes).distinct():
        NotificationApp.objects.create(user=u, titre=titre, corps=corps)
