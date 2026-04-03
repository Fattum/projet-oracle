from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db import IntegrityError, connection
from django.db.models import Count
from django.db.utils import DatabaseError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render

from . import roles
from .decorators import role_required
from .forms import (
    CoursForm,
    CreerCompteEtudiantForm,
    CreerEnseignantForm,
    EtudiantForm,
    InscriptionForm,
    JustifierAbsenceForm,
    SeanceForm,
    PointageGPSForm,
    ProfilAppForm,
    SaisieAbsenceForm,
)
from .models import (
    Absence,
    AnneeUniv,
    Cours,
    Etudiant,
    HistoriqueAlerte,
    Inscription,
    NotificationApp,
    PointageGPS,
    ProfilApp,
    ProfilEtudiant,
    Seance,
)
from .services.oracle_absences import (
    enregistrer_absence_transaction,
    maj_justification_absence,
    notifier_scolarite_nouvelle_absence,
)
from .services.seuil_notifications import (
    corps_notification_sans_marqueur,
    synchroniser_notifications_seuil_etudiant,
)


def _annee_courante():
    try:
        return AnneeUniv.objects.order_by('-date_debut').first()
    except OperationalError:
        return None


def _alertes_seuil_pour_etudiant(etudiant_id):
    """Lignes HISTORIQUE_ALERTE (Oracle trigger ou signal SQLite) pour cet étudiant."""
    try:
        return list(
            HistoriqueAlerte.objects.filter(id_etudiant_id=etudiant_id)
            .select_related('id_cours', 'id_annee')
            .order_by('-date_alerte')[:20]
        )
    except OperationalError:
        return []


@login_required
def accueil(request):
    return redirect('dashboard')


@login_required
def dashboard(request):
    annee = _annee_courante()
    alertes_seuil = []
    try:
        pe = ProfilEtudiant.objects.select_related('etudiant').get(user=request.user)
        alertes_seuil = _alertes_seuil_pour_etudiant(pe.etudiant_id)
        synchroniser_notifications_seuil_etudiant(request.user, alertes_seuil)
    except ProfilEtudiant.DoesNotExist:
        pass
    return render(
        request,
        'absence/dashboard.html',
        {
            'backend_label': connection.vendor,
            'oracle_actif': connection.vendor == 'oracle',
            'annee': annee,
            'alertes_seuil': alertes_seuil,
        },
    )


@role_required(roles.ETUDIANT, roles.ADMIN_APP)
def mes_absences(request):
    context = {'absences': [], 'profil': None, 'erreur': None}

    try:
        try:
            profil = ProfilEtudiant.objects.select_related('etudiant').get(
                user=request.user
            )
        except ProfilEtudiant.DoesNotExist:
            context['erreur'] = 'no_profil'
            return render(request, 'absence/mes_absences.html', context)

        context['profil'] = profil
        context['alertes_seuil'] = _alertes_seuil_pour_etudiant(profil.etudiant_id)
        synchroniser_notifications_seuil_etudiant(
            request.user, context['alertes_seuil']
        )
        context['absences'] = (
            Absence.objects.filter(id_inscription__id_etudiant=profil.etudiant_id)
            .select_related(
                'id_seance',
                'id_inscription',
                'id_inscription__id_cours',
                'id_inscription__id_annee',
            )
            .order_by('-date_saisie', '-id_absence')
        )
    except OperationalError:
        context['erreur'] = 'tables_metier'
        context['profil'] = None
        context['absences'] = []

    return render(request, 'absence/mes_absences.html', context)


@role_required(roles.ENSEIGNANT, roles.ADMIN_APP)
def enseignant_cours(request):
    try:
        cours_list = Cours.objects.all().order_by('code_cours')
    except OperationalError:
        cours_list = []
        messages.warning(
            request,
            'Données indisponibles. Sur votre PC : ouvrez un terminal dans le dossier du '
            'projet et lancez : python manage.py migrate puis python manage.py seed_demo',
        )
    return render(
        request,
        'absence/enseignant_cours.html',
        {'cours_list': cours_list},
    )


@role_required(roles.ENSEIGNANT, roles.ADMIN_APP)
def enseignant_cours_absences(request, cours_id):
    cours = get_object_or_404(Cours, pk=cours_id)
    annee = _annee_courante()
    absences = Absence.objects.filter(id_inscription__id_cours=cours)
    if annee:
        absences = absences.filter(id_inscription__id_annee=annee)
    absences = absences.select_related(
        'id_seance',
        'id_inscription',
        'id_inscription__id_etudiant',
        'id_inscription__id_annee',
    ).order_by('-date_saisie')[:300]
    return render(
        request,
        'absence/enseignant_absences.html',
        {'cours': cours, 'absences': absences, 'annee': annee},
    )


@role_required(roles.ENSEIGNANT, roles.ADMIN_APP)
def enseignant_saisir_absence(request, cours_id):
    cours = get_object_or_404(Cours, pk=cours_id)
    annee = _annee_courante()
    if not annee:
        messages.error(request, 'Il n’y a pas d’année universitaire dans la base. Lancez seed_demo ou ajoutez-en une.')
        return redirect('enseignant_cours')

    ins_qs = (
        Inscription.objects.filter(
            id_cours=cours,
            id_annee=annee,
            statut_insc='VALIDEE',
        )
        .select_related('id_etudiant')
        .order_by('id_etudiant__nom', 'id_etudiant__prenom')
    )
    sea_qs = Seance.objects.filter(id_cours=cours, id_annee=annee).order_by(
        'date_seance', 'heure_debut'
    )

    if request.method == 'POST':
        form = SaisieAbsenceForm(
            request.POST,
            inscriptions_qs=ins_qs,
            seances_qs=sea_qs,
        )
        if form.is_valid():
            ins = form.cleaned_data['inscription']
            sea = form.cleaned_data['seance']
            try:
                enregistrer_absence_transaction(
                    ins.pk,
                    sea.pk,
                    form.cleaned_data['motif'],
                    form.cleaned_data['justifiee'],
                )
                etu = ins.id_etudiant
                notifier_scolarite_nouvelle_absence(
                    cours.code_cours,
                    f'{etu.prenom} {etu.nom} ({etu.matricule})',
                )
                messages.success(
                    request,
                    'L’absence a bien été enregistrée. La scolarité a reçu une notification.',
                )
            except (DatabaseError, ValueError) as exc:
                messages.error(
                    request,
                    f'Impossible d’enregistrer (vérifiez étudiant, séance et doublons). Détail : {exc}',
                )
            return redirect('enseignant_cours_absences', cours_id=cours.pk)
    else:
        form = SaisieAbsenceForm(
            inscriptions_qs=ins_qs,
            seances_qs=sea_qs,
        )

    return render(
        request,
        'absence/enseignant_saisir.html',
        {
            'cours': cours,
            'annee': annee,
            'form': form,
        },
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def scolarite_alertes(request):
    alertes = []
    erreur = None
    try:
        alertes = (
            HistoriqueAlerte.objects.select_related(
                'id_etudiant',
                'id_cours',
                'id_annee',
            )
            .order_by('-date_alerte')[:400]
        )
    except OperationalError:
        erreur = 'tables_metier'
    return render(
        request,
        'absence/scolarite_alertes.html',
        {'alertes': alertes, 'erreur': erreur},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def scolarite_absences_a_traiter(request):
    """Absences non justifiées à traiter (mise à jour via package Oracle en prod)."""
    annee = _annee_courante()
    erreur = None
    absences = []
    if not annee:
        erreur = 'no_annee'
    else:
        try:
            absences = list(
                Absence.objects.filter(
                    id_inscription__id_annee=annee,
                    justifiee='N',
                )
                .select_related(
                    'id_seance',
                    'id_inscription',
                    'id_inscription__id_etudiant',
                    'id_inscription__id_cours',
                    'id_inscription__id_annee',
                )
                .order_by('-date_saisie')[:250]
            )
        except OperationalError:
            erreur = 'tables_metier'
    return render(
        request,
        'absence/scolarite_absences_a_traiter.html',
        {
            'annee': annee,
            'absences': absences,
            'erreur': erreur,
        },
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def scolarite_justifier_absence(request, pk):
    absence = get_object_or_404(
        Absence.objects.select_related(
            'id_seance',
            'id_inscription',
            'id_inscription__id_etudiant',
            'id_inscription__id_cours',
        ),
        pk=pk,
    )
    if request.method == 'POST':
        form = JustifierAbsenceForm(request.POST)
        if form.is_valid():
            try:
                maj_justification_absence(
                    absence.pk,
                    form.cleaned_data['justifiee'],
                    form.cleaned_data['motif'],
                )
                messages.success(request, 'Les modifications ont été enregistrées.')
                return redirect('scolarite_absences_a_traiter')
            except (DatabaseError, ValueError) as exc:
                messages.error(
                    request,
                    f'Enregistrement impossible. Détail : {exc}',
                )
    else:
        form = JustifierAbsenceForm(
            initial={
                'justifiee': absence.justifiee,
                'motif': absence.motif or '',
            }
        )

    return render(
        request,
        'absence/scolarite_justifier.html',
        {
            'absence': absence,
            'form': form,
        },
    )


@login_required
def mon_profil(request):
    try:
        profil, _ = ProfilApp.objects.get_or_create(user=request.user)
    except OperationalError:
        messages.error(
            request,
            'Profil indisponible. Lancez : python manage.py migrate',
        )
        return redirect('dashboard')
    if request.method == 'POST':
        form = ProfilAppForm(request.POST, instance=profil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil enregistré.')
            return redirect('mon_profil')
    else:
        form = ProfilAppForm(instance=profil)
    return render(
        request,
        'absence/mon_profil.html',
        {'form': form, 'profil': profil},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def scolarite_synthese(request):
    annee = _annee_courante()
    stats = []
    erreur = None
    if not annee:
        erreur = 'no_annee'
    else:
        try:
            stats = list(
                Absence.objects.filter(
                    id_inscription__id_annee=annee,
                    justifiee='N',
                )
                .values(
                    'id_inscription__id_etudiant',
                    'id_inscription__id_etudiant__matricule',
                    'id_inscription__id_etudiant__nom',
                    'id_inscription__id_etudiant__prenom',
                )
                .annotate(nb=Count('id_absence'))
                .order_by('-nb')[:40]
            )
        except OperationalError:
            erreur = 'tables_metier'
    return render(
        request,
        'absence/scolarite_synthese.html',
        {
            'annee': annee,
            'stats': stats,
            'erreur': erreur,
        },
    )


@login_required
def notifications_list(request):
    notifs = list(
        NotificationApp.objects.filter(user=request.user).order_by('-date_envoi')[:200]
    )
    for n in notifs:
        n.corps_affiche = corps_notification_sans_marqueur(n.corps)
    return render(
        request,
        'absence/notifications.html',
        {'notifs': notifs},
    )


@login_required
def notification_marquer_lue(request, pk):
    n = get_object_or_404(NotificationApp, pk=pk, user=request.user)
    n.lu = True
    n.save(update_fields=['lu'])
    messages.success(request, 'Notification marquée comme lue.')
    return redirect('notifications')


@role_required(roles.ETUDIANT, roles.ADMIN_APP)
def pointage_gps(request):
    if request.method == 'POST':
        form = PointageGPSForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.user = request.user
            p.save()
            messages.success(request, 'Votre position a été enregistrée.')
            return redirect('pointage_gps')
    else:
        form = PointageGPSForm()

    historique = PointageGPS.objects.filter(user=request.user)[:25]
    return render(
        request,
        'absence/pointage_gps.html',
        {'form': form, 'historique': historique},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_donnees(request):
    """Menu : créer étudiants, cours, comptes enseignants."""
    erreur = None
    try:
        nb_etu = Etudiant.objects.count()
        nb_cours = Cours.objects.count()
    except OperationalError:
        nb_etu = nb_cours = 0
        erreur = 'tables_metier'
    return render(
        request,
        'absence/gestion/index.html',
        {'nb_etu': nb_etu, 'nb_cours': nb_cours, 'erreur': erreur},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_etudiant_nouveau(request):
    try:
        if request.method == 'POST':
            form = EtudiantForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Étudiant créé.')
                return redirect('gestion_donnees')
        else:
            form = EtudiantForm()
    except OperationalError:
        messages.error(request, 'Base indisponible : migrate et seed_demo.')
        return redirect('gestion_donnees')
    return render(request, 'absence/gestion/etudiant_form.html', {'form': form})


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_cours_nouveau(request):
    try:
        if request.method == 'POST':
            form = CoursForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Cours créé.')
                return redirect('gestion_donnees')
        else:
            form = CoursForm()
    except OperationalError:
        messages.error(request, 'Base indisponible : migrate et seed_demo.')
        return redirect('gestion_donnees')
    return render(request, 'absence/gestion/cours_form.html', {'form': form})


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_inscription_nouvelle(request):
    """
    Inscription étudiant → cours → année : sans cela, l’étudiant n’apparaît pas
    dans la liste du professeur pour déclarer une absence.
    """
    try:
        if request.method == 'POST':
            form = InscriptionForm(request.POST)
            if form.is_valid():
                try:
                    form.save()
                except IntegrityError:
                    messages.error(
                        request,
                        'Cette inscription existe déjà (même étudiant, cours et année).',
                    )
                    return render(
                        request,
                        'absence/gestion/inscription_form.html',
                        {'form': form},
                    )
                messages.success(
                    request,
                    'Inscription enregistrée. L’étudiant apparaît maintenant pour ce cours '
                    '(année en cours) lors de la déclaration d’absence.',
                )
                return redirect('gestion_donnees')
        else:
            initial_ins = {
                'date_insc': date.today(),
                'statut_insc': 'VALIDEE',
            }
            cid = request.GET.get('cours')
            aid = request.GET.get('annee')
            if cid:
                try:
                    initial_ins['id_cours'] = int(cid)
                except (ValueError, TypeError):
                    pass
            if aid:
                try:
                    initial_ins['id_annee'] = int(aid)
                except (ValueError, TypeError):
                    pass
            else:
                an = _annee_courante()
                if an and 'id_annee' not in initial_ins:
                    initial_ins['id_annee'] = an.pk
            form = InscriptionForm(initial=initial_ins)
    except OperationalError:
        messages.error(request, 'Base indisponible : migrate et seed_demo.')
        return redirect('gestion_donnees')
    return render(request, 'absence/gestion/inscription_form.html', {'form': form})


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_inscriptions_liste(request):
    """Voir quels étudiants sont inscrits à quels cours (pour comprendre la liste du prof)."""
    try:
        qs = (
            Inscription.objects.filter(statut_insc='VALIDEE')
            .select_related('id_etudiant', 'id_cours', 'id_annee')
            .order_by('id_cours__code_cours', 'id_etudiant__nom', 'id_etudiant__prenom')
        )
        cours_id = request.GET.get('cours')
        if cours_id:
            try:
                qs = qs.filter(id_cours_id=int(cours_id))
            except (ValueError, TypeError):
                pass
        inscriptions = list(qs)
        cours_list = Cours.objects.order_by('code_cours')
    except OperationalError:
        messages.error(request, 'Données indisponibles.')
        return redirect('gestion_donnees')
    return render(
        request,
        'absence/gestion/inscriptions_liste.html',
        {
            'inscriptions': inscriptions,
            'cours_list': cours_list,
            'filtre_cours_id': cours_id,
        },
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_seance_nouvelle(request):
    try:
        initial = {
            'statut_seance': 'REALISEE',
            'heure_debut': Decimal('14.00'),
            'heure_fin': Decimal('16.00'),
        }
        cid = request.GET.get('cours')
        aid = request.GET.get('annee')
        if cid:
            try:
                initial['id_cours'] = int(cid)
            except (ValueError, TypeError):
                pass
        if aid:
            try:
                initial['id_annee'] = int(aid)
            except (ValueError, TypeError):
                pass
        else:
            an = _annee_courante()
            if an:
                initial['id_annee'] = an.pk

        if request.method == 'POST':
            form = SeanceForm(request.POST)
            if form.is_valid():
                try:
                    form.save()
                except IntegrityError:
                    messages.error(
                        request,
                        'Séance déjà existante (même cours, année, date et heure de début).',
                    )
                    return render(
                        request,
                        'absence/gestion/seance_form.html',
                        {'form': form},
                    )
                messages.success(request, 'Séance enregistrée.')
                return redirect('gestion_seances_liste')
        else:
            form = SeanceForm(initial=initial)
    except OperationalError:
        messages.error(request, 'Base indisponible : migrate et seed_demo.')
        return redirect('gestion_donnees')
    return render(request, 'absence/gestion/seance_form.html', {'form': form})


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_seances_liste(request):
    try:
        qs = Seance.objects.select_related('id_cours', 'id_annee').order_by(
            '-date_seance',
            'id_cours__code_cours',
            'heure_debut',
        )
        cours_id = request.GET.get('cours')
        if cours_id:
            try:
                qs = qs.filter(id_cours_id=int(cours_id))
            except (ValueError, TypeError):
                pass
        seances = list(qs[:500])
        cours_list = Cours.objects.order_by('code_cours')
    except OperationalError:
        messages.error(request, 'Données indisponibles.')
        return redirect('gestion_donnees')
    return render(
        request,
        'absence/gestion/seances_liste.html',
        {
            'seances': seances,
            'cours_list': cours_list,
            'filtre_cours_id': cours_id,
        },
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_enseignant_nouveau(request):
    if request.method == 'POST':
        form = CreerEnseignantForm(request.POST)
        if form.is_valid():
            try:
                g = Group.objects.get(name=roles.ENSEIGNANT)
            except Group.DoesNotExist:
                messages.error(
                    request,
                    'Le groupe « Enseignant » est introuvable. Lancez : python manage.py migrate',
                )
                return render(
                    request,
                    'absence/gestion/enseignant_form.html',
                    {'form': form},
                )
            u = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                email=form.cleaned_data.get('email') or '',
            )
            u.groups.add(g)
            messages.success(
                request,
                f'Compte enseignant « {u.username} » créé. L’utilisateur peut se connecter avec le mot de passe choisi.',
            )
            return redirect('gestion_donnees')
    else:
        form = CreerEnseignantForm()
    return render(request, 'absence/gestion/enseignant_form.html', {'form': form})


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_etudiants_liste(request):
    try:
        liens = {
            p.etudiant_id: p.user.username
            for p in ProfilEtudiant.objects.select_related('user')
        }
        etudiants = Etudiant.objects.select_related('id_filiere').order_by('nom', 'prenom')
        lignes = [{'e': e, 'login': liens.get(e.pk)} for e in etudiants]
    except OperationalError:
        messages.error(request, 'Données indisponibles.')
        return redirect('gestion_donnees')
    return render(
        request,
        'absence/gestion/etudiants_liste.html',
        {'lignes': lignes},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_cours_liste(request):
    try:
        cours_list = Cours.objects.all().order_by('code_cours')
    except OperationalError:
        messages.error(request, 'Données indisponibles.')
        return redirect('gestion_donnees')
    return render(
        request,
        'absence/gestion/cours_liste.html',
        {'cours_list': cours_list},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_enseignants_liste(request):
    enseignants = (
        User.objects.filter(groups__name=roles.ENSEIGNANT)
        .distinct()
        .order_by('username')
    )
    return render(
        request,
        'absence/gestion/enseignants_liste.html',
        {'enseignants': enseignants},
    )


@role_required(roles.SCOLARITE, roles.ADMIN_APP)
def gestion_compte_etudiant_nouveau(request):
    """
    Compte de connexion + groupe Étudiant + lien ProfilEtudiant.
    """
    try:
        if request.method == 'POST':
            form = CreerCompteEtudiantForm(request.POST)
            if form.is_valid():
                try:
                    g_etu = Group.objects.get(name=roles.ETUDIANT)
                except Group.DoesNotExist:
                    messages.error(
                        request,
                        'Le groupe « Etudiant » est introuvable. Lancez : python manage.py migrate',
                    )
                    return render(
                        request,
                        'absence/gestion/compte_etudiant_form.html',
                        {'form': form},
                    )
                etu = form.cleaned_data['etudiant']
                u = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password'],
                    email=form.cleaned_data.get('email') or '',
                )
                u.groups.add(g_etu)
                ProfilEtudiant.objects.create(user=u, etudiant=etu)
                messages.success(
                    request,
                    f'Compte créé. L’étudiant se connecte avec l’identifiant « {u.username} » '
                    'et le mot de passe choisi (page Connexion).',
                )
                return redirect('gestion_donnees')
        else:
            form = CreerCompteEtudiantForm()
    except OperationalError:
        messages.error(request, 'Base indisponible : migrate et seed_demo.')
        return redirect('gestion_donnees')
    return render(
        request,
        'absence/gestion/compte_etudiant_form.html',
        {'form': form},
    )
