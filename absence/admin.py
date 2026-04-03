from django.contrib import admin

from . import models


@admin.register(models.Filiere)
class FiliereAdmin(admin.ModelAdmin):
    list_display = ('id_filiere', 'code_filiere', 'nom_filiere')


@admin.register(models.AnneeUniv)
class AnneeUnivAdmin(admin.ModelAdmin):
    list_display = ('id_annee', 'libelle', 'date_debut', 'date_fin')


@admin.register(models.Cours)
class CoursAdmin(admin.ModelAdmin):
    list_display = ('id_cours', 'code_cours', 'intitule', 'coef')


@admin.register(models.Etudiant)
class EtudiantAdmin(admin.ModelAdmin):
    list_display = ('id_etudiant', 'matricule', 'nom', 'prenom', 'statut', 'id_filiere')
    list_filter = ('statut', 'id_filiere')
    search_fields = ('matricule', 'nom', 'prenom', 'email')


@admin.register(models.Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('id_inscription', 'id_etudiant', 'id_cours', 'id_annee', 'statut_insc')


@admin.register(models.Seance)
class SeanceAdmin(admin.ModelAdmin):
    list_display = ('id_seance', 'id_cours', 'id_annee', 'date_seance', 'statut_seance')


@admin.register(models.ParamGlobalAnnee)
class ParamGlobalAnneeAdmin(admin.ModelAdmin):
    list_display = ('id_annee', 'seuil_non_justif')


@admin.register(models.ParamCoursSeuil)
class ParamCoursSeuilAdmin(admin.ModelAdmin):
    list_display = ('id_param', 'id_cours', 'id_annee', 'seuil_non_justif')


@admin.register(models.Absence)
class AbsenceAdmin(admin.ModelAdmin):
    list_display = ('id_absence', 'id_inscription', 'id_seance', 'justifiee', 'date_saisie')


@admin.register(models.HistoriqueAlerte)
class HistoriqueAlerteAdmin(admin.ModelAdmin):
    list_display = ('id_alerte', 'id_etudiant', 'id_cours', 'nb_abs_non_just', 'date_alerte')


@admin.register(models.ProfilEtudiant)
class ProfilEtudiantAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'etudiant')
    autocomplete_fields = ('user', 'etudiant')


@admin.register(models.NotificationApp)
class NotificationAppAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'titre', 'lu', 'date_envoi')
    list_filter = ('lu',)


@admin.register(models.PointageGPS)
class PointageGPSAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'contexte', 'horodatage', 'latitude', 'longitude')


@admin.register(models.ProfilApp)
class ProfilAppAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'nom_affiche', 'telephone')
    search_fields = ('user__username', 'nom_affiche', 'telephone')
