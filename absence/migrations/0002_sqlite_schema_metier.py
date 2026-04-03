"""
Crée les tables métier sur SQLite (développement local sans Oracle).
Sur Oracle / PostgreSQL / etc. : aucune opération (schéma déjà fourni par les scripts SQL).
"""

from django.db import migrations


SQLITE_DDLS = [
    """
    CREATE TABLE IF NOT EXISTS "FILIERE" (
        "ID_FILIERE" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "CODE_FILIERE" varchar(10) NOT NULL UNIQUE,
        "NOM_FILIERE" varchar(100) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "ANNEE_UNIV" (
        "ID_ANNEE" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "LIBELLE" varchar(30) NOT NULL UNIQUE,
        "DATE_DEBUT" date NOT NULL,
        "DATE_FIN" date NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "COURS" (
        "ID_COURS" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "CODE_COURS" varchar(20) NOT NULL UNIQUE,
        "INTITULE" varchar(200) NOT NULL,
        "COEF" decimal NOT NULL,
        "NB_SEANCES_PREV" integer NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "ETUDIANT" (
        "ID_ETUDIANT" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "MATRICULE" varchar(20) NOT NULL UNIQUE,
        "NOM" varchar(80) NOT NULL,
        "PRENOM" varchar(80) NOT NULL,
        "EMAIL" varchar(120) NULL UNIQUE,
        "DATE_NAISSANCE" date NULL,
        "ID_FILIERE" integer NOT NULL REFERENCES "FILIERE" ("ID_FILIERE") DEFERRABLE INITIALLY DEFERRED,
        "STATUT" varchar(20) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "INSCRIPTION" (
        "ID_INSCRIPTION" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "ID_ETUDIANT" integer NOT NULL REFERENCES "ETUDIANT" ("ID_ETUDIANT") DEFERRABLE INITIALLY DEFERRED,
        "ID_COURS" integer NOT NULL REFERENCES "COURS" ("ID_COURS") DEFERRABLE INITIALLY DEFERRED,
        "ID_ANNEE" integer NOT NULL REFERENCES "ANNEE_UNIV" ("ID_ANNEE") DEFERRABLE INITIALLY DEFERRED,
        "DATE_INSC" date NOT NULL,
        "STATUT_INSC" varchar(20) NOT NULL,
        UNIQUE ("ID_ETUDIANT", "ID_COURS", "ID_ANNEE")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "SEANCE" (
        "ID_SEANCE" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "ID_COURS" integer NOT NULL REFERENCES "COURS" ("ID_COURS") DEFERRABLE INITIALLY DEFERRED,
        "ID_ANNEE" integer NOT NULL REFERENCES "ANNEE_UNIV" ("ID_ANNEE") DEFERRABLE INITIALLY DEFERRED,
        "DATE_SEANCE" date NOT NULL,
        "HEURE_DEBUT" decimal NOT NULL,
        "HEURE_FIN" decimal NOT NULL,
        "STATUT_SEANCE" varchar(20) NOT NULL,
        UNIQUE ("ID_COURS", "ID_ANNEE", "DATE_SEANCE", "HEURE_DEBUT")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "PARAM_GLOBAL_ANNEE" (
        "ID_ANNEE" integer NOT NULL PRIMARY KEY REFERENCES "ANNEE_UNIV" ("ID_ANNEE") DEFERRABLE INITIALLY DEFERRED,
        "SEUIL_NON_JUSTIF" integer NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "PARAM_COURS_SEUIL" (
        "ID_PARAM" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "ID_COURS" integer NOT NULL REFERENCES "COURS" ("ID_COURS") DEFERRABLE INITIALLY DEFERRED,
        "ID_ANNEE" integer NOT NULL REFERENCES "ANNEE_UNIV" ("ID_ANNEE") DEFERRABLE INITIALLY DEFERRED,
        "SEUIL_NON_JUSTIF" integer NOT NULL,
        UNIQUE ("ID_COURS", "ID_ANNEE")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "ABSENCE" (
        "ID_ABSENCE" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "ID_INSCRIPTION" integer NOT NULL REFERENCES "INSCRIPTION" ("ID_INSCRIPTION") DEFERRABLE INITIALLY DEFERRED,
        "ID_SEANCE" integer NOT NULL REFERENCES "SEANCE" ("ID_SEANCE") DEFERRABLE INITIALLY DEFERRED,
        "MOTIF" varchar(300) NULL,
        "JUSTIFIEE" varchar(1) NOT NULL,
        "DATE_SAISIE" datetime NOT NULL,
        UNIQUE ("ID_INSCRIPTION", "ID_SEANCE")
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS "HISTORIQUE_ALERTE" (
        "ID_ALERTE" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "ID_ETUDIANT" integer NOT NULL REFERENCES "ETUDIANT" ("ID_ETUDIANT") DEFERRABLE INITIALLY DEFERRED,
        "ID_COURS" integer NOT NULL REFERENCES "COURS" ("ID_COURS") DEFERRABLE INITIALLY DEFERRED,
        "ID_ANNEE" integer NOT NULL REFERENCES "ANNEE_UNIV" ("ID_ANNEE") DEFERRABLE INITIALLY DEFERRED,
        "NB_ABS_NON_JUST" integer NOT NULL,
        "DATE_ALERTE" datetime NOT NULL,
        "MESSAGE" varchar(500) NOT NULL
    );
    """,
]

SQLITE_DROP_ORDER = [
    'HISTORIQUE_ALERTE',
    'ABSENCE',
    'PARAM_COURS_SEUIL',
    'PARAM_GLOBAL_ANNEE',
    'SEANCE',
    'INSCRIPTION',
    'ETUDIANT',
    'COURS',
    'ANNEE_UNIV',
    'FILIERE',
]


def _create_sqlite(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    with schema_editor.connection.cursor() as cursor:
        for ddl in SQLITE_DDLS:
            cursor.execute(ddl)


def _drop_sqlite(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys = OFF')
        for name in SQLITE_DROP_ORDER:
            cursor.execute(f'DROP TABLE IF EXISTS "{name}"')
        cursor.execute('PRAGMA foreign_keys = ON')


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(_create_sqlite, _drop_sqlite),
    ]
