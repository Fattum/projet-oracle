from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('', views.accueil, name='accueil'),
    path('tableau-de-bord/', views.dashboard, name='dashboard'),
    path(
        'accounts/login/',
        auth_views.LoginView.as_view(template_name='absence/login.html'),
        name='login',
    ),
    path(
        'accounts/logout/',
        auth_views.LogoutView.as_view(),
        name='logout',
    ),
    path('mes-absences/', views.mes_absences, name='mes_absences'),
    path('enseignant/cours/', views.enseignant_cours, name='enseignant_cours'),
    path(
        'enseignant/cours/<int:cours_id>/absences/',
        views.enseignant_cours_absences,
        name='enseignant_cours_absences',
    ),
    path(
        'enseignant/cours/<int:cours_id>/saisir/',
        views.enseignant_saisir_absence,
        name='enseignant_saisir_absence',
    ),
    path('scolarite/alertes/', views.scolarite_alertes, name='scolarite_alertes'),
    path(
        'scolarite/absences-a-traiter/',
        views.scolarite_absences_a_traiter,
        name='scolarite_absences_a_traiter',
    ),
    path(
        'scolarite/absence/<int:pk>/justifier/',
        views.scolarite_justifier_absence,
        name='scolarite_justifier_absence',
    ),
    path(
        'scolarite/synthese/',
        views.scolarite_synthese,
        name='scolarite_synthese',
    ),
    path('mon-profil/', views.mon_profil, name='mon_profil'),
    path('gestion/', views.gestion_donnees, name='gestion_donnees'),
    path('gestion/etudiants/', views.gestion_etudiants_liste, name='gestion_etudiants_liste'),
    path('gestion/cours/liste/', views.gestion_cours_liste, name='gestion_cours_liste'),
    path('gestion/enseignants/', views.gestion_enseignants_liste, name='gestion_enseignants_liste'),
    path('gestion/etudiant/nouveau/', views.gestion_etudiant_nouveau, name='gestion_etudiant_nouveau'),
    path(
        'gestion/compte-etudiant/nouveau/',
        views.gestion_compte_etudiant_nouveau,
        name='gestion_compte_etudiant_nouveau',
    ),
    path('gestion/cours/nouveau/', views.gestion_cours_nouveau, name='gestion_cours_nouveau'),
    path(
        'gestion/inscription/nouvelle/',
        views.gestion_inscription_nouvelle,
        name='gestion_inscription_nouvelle',
    ),
    path(
        'gestion/inscriptions/',
        views.gestion_inscriptions_liste,
        name='gestion_inscriptions_liste',
    ),
    path(
        'gestion/seance/nouvelle/',
        views.gestion_seance_nouvelle,
        name='gestion_seance_nouvelle',
    ),
    path('gestion/seances/', views.gestion_seances_liste, name='gestion_seances_liste'),
    path(
        'gestion/enseignant/nouveau/',
        views.gestion_enseignant_nouveau,
        name='gestion_enseignant_nouveau',
    ),
    path('notifications/', views.notifications_list, name='notifications'),
    path(
        'notifications/<int:pk>/lue/',
        views.notification_marquer_lue,
        name='notification_lue',
    ),
    path('etudiant/pointage-gps/', views.pointage_gps, name='pointage_gps'),
]
