from django import forms
from django.contrib.auth.models import User

from .models import (
    AnneeUniv,
    Cours,
    Etudiant,
    Inscription,
    ProfilApp,
    ProfilEtudiant,
    Seance,
)


def _style_widgets(form):
    for f in form.fields.values():
        w = f.widget
        if isinstance(
            w,
            (
                forms.TextInput,
                forms.NumberInput,
                forms.EmailInput,
                forms.DateInput,
                forms.PasswordInput,
            ),
        ):
            w.attrs.setdefault('class', 'input')
        if isinstance(w, forms.Select):
            w.attrs.setdefault('class', 'input')
        if isinstance(w, forms.Textarea):
            w.attrs.setdefault('class', 'input')


class EtudiantForm(forms.ModelForm):
    class Meta:
        model = Etudiant
        fields = (
            'matricule',
            'nom',
            'prenom',
            'email',
            'date_naissance',
            'id_filiere',
            'statut',
        )
        labels = {
            'id_filiere': 'Filière',
            'matricule': 'Matricule',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)

    def clean_email(self):
        e = self.cleaned_data.get('email')
        if e is None or not str(e).strip():
            return None
        return str(e).strip()


class CoursForm(forms.ModelForm):
    class Meta:
        model = Cours
        fields = ('code_cours', 'intitule', 'coef', 'nb_seances_prev')
        labels = {
            'code_cours': 'Code du cours',
            'intitule': 'Intitulé',
            'coef': 'Coefficient',
            'nb_seances_prev': 'Nombre de séances prévues',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)


class CreerEnseignantForm(forms.Form):
    username = forms.CharField(label="Nom d'utilisateur", max_length=150)
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password_confirm = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput,
    )
    email = forms.EmailField(label='E-mail', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError('Ce nom d’utilisateur existe déjà.')
        return u

    def clean(self):
        data = super().clean()
        p1 = data.get('password')
        p2 = data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Les mots de passe ne correspondent pas.')
        return data


class EtudiantSansCompteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.matricule} — {obj.prenom} {obj.nom}'


class InscriptionForm(forms.ModelForm):
    """Inscrire un étudiant à un cours pour une année (obligatoire pour la saisie d’absence)."""

    class Meta:
        model = Inscription
        fields = ('id_etudiant', 'id_cours', 'id_annee', 'date_insc', 'statut_insc')
        labels = {
            'id_etudiant': 'Étudiant',
            'id_cours': 'Cours',
            'id_annee': 'Année universitaire',
            'date_insc': "Date d'inscription",
            'statut_insc': "Statut de l'inscription",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)
        self.fields['id_etudiant'].queryset = Etudiant.objects.filter(
            statut='ACTIF',
        ).order_by('nom', 'prenom')
        self.fields['id_cours'].queryset = Cours.objects.order_by('code_cours')
        self.fields['id_annee'].queryset = AnneeUniv.objects.order_by('-date_debut')

    def clean(self):
        data = super().clean()
        etu = data.get('id_etudiant')
        crs = data.get('id_cours')
        an = data.get('id_annee')
        if etu and crs and an:
            if Inscription.objects.filter(
                id_etudiant=etu,
                id_cours=crs,
                id_annee=an,
            ).exists():
                self.add_error(
                    None,
                    'Cette inscription existe déjà pour cet étudiant, ce cours et cette année.',
                )
        return data


class SeanceForm(forms.ModelForm):
    """Planifier une séance (date + créneau) pour un cours et une année."""

    class Meta:
        model = Seance
        fields = (
            'id_cours',
            'id_annee',
            'date_seance',
            'heure_debut',
            'heure_fin',
            'statut_seance',
        )
        labels = {
            'id_cours': 'Cours',
            'id_annee': 'Année universitaire',
            'date_seance': 'Date de la séance',
            'heure_debut': 'Heure début (ex. 14 = 14h00)',
            'heure_fin': 'Heure fin (ex. 16 = 16h00)',
            'statut_seance': 'Statut de la séance',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)
        self.fields['id_cours'].queryset = Cours.objects.order_by('code_cours')
        self.fields['id_annee'].queryset = AnneeUniv.objects.order_by('-date_debut')

    def clean(self):
        data = super().clean()
        d = data.get('heure_debut')
        f = data.get('heure_fin')
        if d is not None and f is not None and f <= d:
            self.add_error('heure_fin', 'L’heure de fin doit être strictement après l’heure de début.')
        crs = data.get('id_cours')
        an = data.get('id_annee')
        ds = data.get('date_seance')
        if crs and an and ds and d is not None:
            if Seance.objects.filter(
                id_cours=crs,
                id_annee=an,
                date_seance=ds,
                heure_debut=d,
            ).exists():
                self.add_error(
                    None,
                    'Une séance existe déjà à cette date et à cette heure pour ce cours.',
                )
        return data


class CreerCompteEtudiantForm(forms.Form):
    """
    Crée un utilisateur Django (groupe Étudiant) et le lie à une fiche ETUDIANT.
    Sans ce lien, l’étudiant ne peut pas voir « Mes absences ».
    """

    etudiant = EtudiantSansCompteChoiceField(
        label='Étudiant (fiche dans la base)',
        queryset=Etudiant.objects.none(),
    )
    username = forms.CharField(label="Nom d'utilisateur pour la connexion", max_length=150)
    password = forms.CharField(label='Mot de passe', widget=forms.PasswordInput)
    password_confirm = forms.CharField(
        label='Confirmer le mot de passe',
        widget=forms.PasswordInput,
    )
    email = forms.EmailField(label='E-mail', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style_widgets(self)
        linked_ids = ProfilEtudiant.objects.values_list('etudiant_id', flat=True)
        self.fields['etudiant'].queryset = (
            Etudiant.objects.exclude(pk__in=linked_ids)
            .order_by('nom', 'prenom')
        )

    def clean_username(self):
        u = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError('Ce nom d’utilisateur existe déjà.')
        return u

    def clean_etudiant(self):
        e = self.cleaned_data['etudiant']
        if ProfilEtudiant.objects.filter(etudiant=e).exists():
            raise forms.ValidationError(
                'Cet étudiant a déjà un compte. Utilisez un autre étudiant ou modifiez le lien dans l’admin Django.'
            )
        return e

    def clean(self):
        data = super().clean()
        p1 = data.get('password')
        p2 = data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Les mots de passe ne correspondent pas.')
        return data


class InscriptionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        e = obj.id_etudiant
        return f'{e.matricule} — {e.prenom} {e.nom}'


class SeanceChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return (
            f'{obj.date_seance} ({obj.heure_debut}–{obj.heure_fin}h) — '
            f'{obj.get_statut_seance_display()}'
        )


class SaisieAbsenceForm(forms.Form):
    inscription = InscriptionChoiceField(
        label='Étudiant (inscription)',
        queryset=Inscription.objects.none(),
    )
    seance = SeanceChoiceField(
        label='Séance',
        queryset=Seance.objects.none(),
    )
    motif = forms.CharField(
        label='Motif',
        required=False,
        widget=forms.Textarea(attrs={'rows': 3}),
    )
    justifiee = forms.ChoiceField(
        label='Justifiée',
        choices=[('N', 'Non'), ('O', 'Oui')],
        initial='N',
    )

    def __init__(self, *args, inscriptions_qs=None, seances_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        if inscriptions_qs is not None:
            self.fields['inscription'].queryset = inscriptions_qs
        if seances_qs is not None:
            self.fields['seance'].queryset = seances_qs
        for _n, f in self.fields.items():
            w = f.widget
            if isinstance(w, (forms.Select, forms.Textarea)):
                w.attrs.setdefault('class', 'input')


class JustifierAbsenceForm(forms.Form):
    justifiee = forms.ChoiceField(
        label='Justifiée',
        choices=[('N', 'Non'), ('O', 'Oui')],
    )
    motif = forms.CharField(
        label='Motif / commentaire scolarité',
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _n, f in self.fields.items():
            w = f.widget
            if isinstance(w, (forms.Select, forms.Textarea)):
                w.attrs.setdefault('class', 'input')


class ProfilAppForm(forms.ModelForm):
    class Meta:
        model = ProfilApp
        fields = ('nom_affiche', 'telephone')
        widgets = {
            'nom_affiche': forms.TextInput(
                attrs={'class': 'input', 'placeholder': 'Prénom Nom'}
            ),
            'telephone': forms.TextInput(
                attrs={'class': 'input', 'placeholder': '+212 …'}
            ),
        }
