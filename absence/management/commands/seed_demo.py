"""
Données de démonstration + comptes par rôle (groupes Django).

Comptes (mot de passe par défaut : demo123) :
  - etudiant   → groupe Etudiant (+ profil DEMO001 si tables métier)
  - prof       → groupe Enseignant
  - scolarite  → groupe Scolarite
  - adminapp   → groupe Admin_application, is_staff=True (accès /admin/)

  python manage.py seed_demo
  python manage.py seed_demo --password monpass
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError
from django.utils import timezone

from absence import roles
from absence.models import (
    Absence,
    AnneeUniv,
    Cours,
    Etudiant,
    Filiere,
    Inscription,
    ParamCoursSeuil,
    ParamGlobalAnnee,
    ProfilApp,
    ProfilEtudiant,
    Seance,
)


def _tables_metier_presentes():
    noms = {t.lower() for t in connection.introspection.table_names()}
    return 'etudiant' in noms


def _ensure_group(name):
    g, _ = Group.objects.get_or_create(name=name)
    return g


def _set_user(username, email, password, groups, *, is_staff=False):
    u, created = User.objects.get_or_create(
        username=username,
        defaults={'email': email, 'is_staff': is_staff},
    )
    u.email = email
    u.is_staff = is_staff
    u.set_password(password)
    u.save()
    u.groups.clear()
    for g in groups:
        u.groups.add(g)
    return u, created


class Command(BaseCommand):
    help = 'Jeux de démo : tables métier + utilisateurs par rôle'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='demo123',
            help='Mot de passe pour tous les comptes de démo',
        )

    def handle(self, *args, **options):
        password = options['password']

        for name in roles.ALL_ROLES:
            _ensure_group(name)

        g_etu = Group.objects.get(name=roles.ETUDIANT)
        g_ens = Group.objects.get(name=roles.ENSEIGNANT)
        g_sco = Group.objects.get(name=roles.SCOLARITE)
        g_adm = Group.objects.get(name=roles.ADMIN_APP)

        u_etu, _ = _set_user(
            'etudiant',
            'etudiant@demo.local',
            password,
            [g_etu],
        )
        _set_user('prof', 'prof@demo.local', password, [g_ens])
        _set_user('scolarite', 'scolarite@demo.local', password, [g_sco])
        _set_user(
            'adminapp',
            'adminapp@demo.local',
            password,
            [g_adm],
            is_staff=True,
        )

        noms = {
            'etudiant': 'Sara Alami (démo)',
            'prof': 'Prof. Démo',
            'scolarite': 'Service scolarité',
            'adminapp': 'Administrateur appli',
        }
        try:
            for username, label in noms.items():
                u = User.objects.get(username=username)
                ProfilApp.objects.update_or_create(
                    user=u,
                    defaults={'nom_affiche': label},
                )
        except OperationalError:
            self.stdout.write(
                self.style.WARNING(
                    'Profils applicatifs : exécutez migrate (0004) pour ABSENCE_PROFIL_APP.'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                'Comptes : etudiant, prof, scolarite, adminapp -- mot de passe = '
                f'"{password}"'
            )
        )

        if not _tables_metier_presentes():
            self.stdout.write(
                self.style.WARNING(
                    'Tables métier absentes : migrate + SQLite (0002) ou Oracle '
                    '(scripts oracle/). Puis relancez seed_demo pour les données.'
                )
            )
            return

        try:
            self._seed_metier(u_etu)
        except OperationalError as e:
            self.stdout.write(self.style.ERROR(f'Erreur base : {e}'))

    def _seed_metier(self, user_etudiant):
        filiere, _ = Filiere.objects.get_or_create(
            code_filiere='INFO',
            defaults={'nom_filiere': 'Informatique de gestion'},
        )

        annee, _ = AnneeUniv.objects.get_or_create(
            libelle='2024-2025',
            defaults={
                'date_debut': date(2024, 9, 1),
                'date_fin': date(2025, 7, 15),
            },
        )

        cours, _ = Cours.objects.get_or_create(
            code_cours='BD501',
            defaults={
                'intitule': 'Bases de données avancées',
                'coef': Decimal('3.00'),
                'nb_seances_prev': 28,
            },
        )

        etu, _ = Etudiant.objects.get_or_create(
            matricule='DEMO001',
            defaults={
                'nom': 'Alami',
                'prenom': 'Sara',
                'email': 'sara.demo@etudiant.local',
                'date_naissance': date(2002, 5, 10),
                'id_filiere': filiere,
                'statut': 'ACTIF',
            },
        )

        ParamGlobalAnnee.objects.get_or_create(
            id_annee=annee,
            defaults={'seuil_non_justif': 3},
        )

        ParamCoursSeuil.objects.update_or_create(
            id_cours=cours,
            id_annee=annee,
            defaults={'seuil_non_justif': 3},
        )

        ins, _ = Inscription.objects.get_or_create(
            id_etudiant=etu,
            id_cours=cours,
            id_annee=annee,
            defaults={
                'date_insc': date.today(),
                'statut_insc': 'VALIDEE',
            },
        )

        h14 = Decimal('14.00')
        h16 = Decimal('16.00')
        sea1, _ = Seance.objects.get_or_create(
            id_cours=cours,
            id_annee=annee,
            date_seance=date(2024, 10, 15),
            heure_debut=h14,
            defaults={
                'heure_fin': h16,
                'statut_seance': 'REALISEE',
            },
        )

        sea2, _ = Seance.objects.get_or_create(
            id_cours=cours,
            id_annee=annee,
            date_seance=date(2024, 10, 22),
            heure_debut=h14,
            defaults={
                'heure_fin': h16,
                'statut_seance': 'REALISEE',
            },
        )
        # Séances supplémentaires (sans absence) pour tester le seuil = 3 absences non justifiées
        Seance.objects.get_or_create(
            id_cours=cours,
            id_annee=annee,
            date_seance=date(2024, 10, 29),
            heure_debut=h14,
            defaults={
                'heure_fin': h16,
                'statut_seance': 'REALISEE',
            },
        )
        Seance.objects.get_or_create(
            id_cours=cours,
            id_annee=annee,
            date_seance=date(2024, 11, 5),
            heure_debut=h14,
            defaults={
                'heure_fin': h16,
                'statut_seance': 'REALISEE',
            },
        )

        now = timezone.now()
        Absence.objects.get_or_create(
            id_inscription=ins,
            id_seance=sea1,
            defaults={
                'motif': 'Rendez-vous médical',
                'justifiee': 'O',
                'date_saisie': now,
            },
        )
        Absence.objects.get_or_create(
            id_inscription=ins,
            id_seance=sea2,
            defaults={
                'motif': 'Transport en panne',
                'justifiee': 'N',
                'date_saisie': now,
            },
        )

        ProfilEtudiant.objects.update_or_create(
            etudiant=etu,
            defaults={'user': user_etudiant},
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Donnees metier + lien etudiant DEMO001 -> utilisateur "etudiant".'
            )
        )
