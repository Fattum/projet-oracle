-- =============================================================================
-- Rôle Oracle technique + privilèges minimaux (à exécuter en DBA : SYS / SYSTEM)
--
-- Remplacez :
--   &OWNER_SCHEMA  → propriétaire des tables (ex. ABSENCES_APP)
--   &TECH_USER     → utilisateur Django / cx_Oracle (ex. DJANGO_ORA_TECH)
--
-- L’utilisateur technique n’est PAS un utilisateur métier : il sert uniquement
-- à la connexion applicative (Django). Les comptes finaux restent dans Django.
-- =============================================================================

-- Création du rôle (droits réutilisables sur les objets du schéma métier)
CREATE ROLE R_APP_ABSENCES;

-- Note : selon la version Oracle, CREATE SESSION est parfois accordé directement
-- à l’utilisateur technique plutôt qu’au rôle. En cas d’erreur, exécuter :
--   GRANT CREATE SESSION TO &TECH_USER;

-- Tables métier : CRUD nécessaire à l’application
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..FILIERE TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..ANNEE_UNIV TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..COURS TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..ETUDIANT TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..INSCRIPTION TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..SEANCE TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..PARAM_GLOBAL_ANNEE TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..PARAM_COURS_SEUIL TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..ABSENCE TO R_APP_ABSENCES;
GRANT SELECT, INSERT, UPDATE, DELETE ON &OWNER_SCHEMA..HISTORIQUE_ALERTE TO R_APP_ABSENCES;

-- Package (procédures / fonctions métier)
GRANT EXECUTE ON &OWNER_SCHEMA..PKG_GESTION_ABSENCES TO R_APP_ABSENCES;

-- Séquences (INSERT via triggers BI si NULL — droits souvent requis)
GRANT SELECT ON &OWNER_SCHEMA..FILIERE_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..ANNEE_UNIV_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..COURS_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..ETUDIANT_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..INSCRIPTION_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..SEANCE_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..ABSENCE_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..HISTORIQUE_ALERTE_SQ TO R_APP_ABSENCES;
GRANT SELECT ON &OWNER_SCHEMA..PARAM_COURS_SEUIL_SQ TO R_APP_ABSENCES;

-- Utilisateur technique : session + rôle (quota seulement si l’utilisateur possède des objets)
-- CREATE USER &TECH_USER IDENTIFIED BY "********";
-- GRANT CREATE SESSION TO &TECH_USER;
-- GRANT R_APP_ABSENCES TO &TECH_USER;
-- ALTER USER &TECH_USER DEFAULT TABLESPACE USERS QUOTA UNLIMITED ON USERS;
-- (Quota requis seulement si l’utilisateur doit posséder des objets — ici non.)

/*
 * Variante sans substitution SQL*Plus : exécuter en remplaçant manuellement
 * OWNER_SCHEMA et en accordant au user Django :
 *
 * GRANT R_APP_ABSENCES TO DJANGO_ORA_TECH;
 */
