"""
Scénario complet pour tester cours + séances + inscription + absences + alerte (seuil 3).

  python manage.py migrate
  python manage.py seed_demo
  python manage.py seed_scenario_alerte

Puis suivre GUIDE_TEST_ALERTES.txt (ou les instructions affichées en fin de commande).
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError

from absence.models import (
    AnneeUniv,
    Cours,
    Etudiant,
    Filiere,
    Inscription,
    ParamCoursSeuil,
    Seance,
)


def _tables_ok():
    noms = {t.lower() for t in connection.introspection.table_names()}
    return 'etudiant' in noms and 'cours' in noms


class Command(BaseCommand):
    help = 'Données de test : cours ALERT01, 1 étudiant, 4 séances, seuil 3'

    def handle(self, *args, **options):
        if not _tables_ok():
            self.stderr.write(
                self.style.ERROR('Tables métier absentes : lancez migrate puis seed_demo.')
            )
            return

        try:
            filiere = Filiere.objects.order_by('pk').first()
            if not filiere:
                filiere, _ = Filiere.objects.get_or_create(
                    code_filiere='INFO',
                    defaults={'nom_filiere': 'Informatique de gestion'},
                )

            annee = AnneeUniv.objects.order_by('-date_debut').first()
            if not annee:
                self.stderr.write(
                    self.style.ERROR('Aucune année universitaire : lancez seed_demo.')
                )
                return

            cours, _ = Cours.objects.get_or_create(
                code_cours='ALERT01',
                defaults={
                    'intitule': 'Cours démo — test des alertes',
                    'coef': Decimal('2.00'),
                    'nb_seances_prev': 20,
                },
            )

            etu, _ = Etudiant.objects.get_or_create(
                matricule='ALERT_ETU1',
                defaults={
                    'nom': 'Dupont',
                    'prenom': 'Alex',
                    'email': 'alex.alert01@demo.local',
                    'date_naissance': date(2003, 3, 15),
                    'id_filiere': filiere,
                    'statut': 'ACTIF',
                },
            )

            Inscription.objects.get_or_create(
                id_etudiant=etu,
                id_cours=cours,
                id_annee=annee,
                defaults={
                    'date_insc': date.today(),
                    'statut_insc': 'VALIDEE',
                },
            )

            ParamCoursSeuil.objects.update_or_create(
                id_cours=cours,
                id_annee=annee,
                defaults={'seuil_non_justif': 3},
            )

            h_deb = Decimal('10.00')
            h_fin = Decimal('12.00')
            dates = [
                date(2024, 11, 6),
                date(2024, 11, 13),
                date(2024, 11, 20),
                date(2024, 11, 27),
            ]
            for d in dates:
                Seance.objects.get_or_create(
                    id_cours=cours,
                    id_annee=annee,
                    date_seance=d,
                    heure_debut=h_deb,
                    defaults={
                        'heure_fin': h_fin,
                        'statut_seance': 'REALISEE',
                    },
                )

        except OperationalError as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        self.stdout.write(self.style.SUCCESS('Scénario ALERT01 créé ou mis à jour.'))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=== TEST PAS À PAS ==='))
        self.stdout.write('')
        self.stdout.write('1) Lancez le serveur : python manage.py runserver')
        self.stdout.write('')
        self.stdout.write('2) Connectez-vous en ENSEIGNANT :')
        self.stdout.write('   Utilisateur : prof')
        self.stdout.write('   Mot de passe : demo123 (ou celui de seed_demo)')
        self.stdout.write('')
        self.stdout.write('3) Menu Enseignant : ouvrez le cours ALERT01 puis Saisir')
        self.stdout.write('')
        self.stdout.write('4) Trois fois de suite :')
        self.stdout.write('   - Étudiant : ALERT_ETU1 — Alex Dupont')
        self.stdout.write('   - Séance : une date différente à chaque fois (4 séances dispo)')
        self.stdout.write('   - Justifiée : Non')
        self.stdout.write('   - Enregistrer')
        self.stdout.write('')
        self.stdout.write('5) À la 3e absence NON justifiée, une alerte est créée :')
        self.stdout.write('   - SQLite : automatique (signal Django, seuil = 3)')
        self.stdout.write('   - Oracle : automatique (trigger base)')
        self.stdout.write('')
        self.stdout.write('6) Déconnectez-vous, connectez-vous en SCOLARITÉ :')
        self.stdout.write('   Utilisateur : scolarite / mot de passe demo123')
        self.stdout.write('')
        self.stdout.write('7) Menu Alertes : une ligne pour Alex Dupont / ALERT01.')
        self.stdout.write('')
        self.stdout.write('Fichier détaillé : GUIDE_TEST_ALERTES.txt à la racine du projet.')
