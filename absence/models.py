from django.contrib.auth.models import User
from django.db import models


class Filiere(models.Model):
    id_filiere = models.AutoField(primary_key=True, db_column='ID_FILIERE')
    code_filiere = models.CharField(max_length=10, db_column='CODE_FILIERE')
    nom_filiere = models.CharField(max_length=100, db_column='NOM_FILIERE')

    class Meta:
        managed = False
        db_table = 'FILIERE'

    def __str__(self):
        return self.nom_filiere


class AnneeUniv(models.Model):
    id_annee = models.AutoField(primary_key=True, db_column='ID_ANNEE')
    libelle = models.CharField(max_length=30, db_column='LIBELLE')
    date_debut = models.DateField(db_column='DATE_DEBUT')
    date_fin = models.DateField(db_column='DATE_FIN')

    class Meta:
        managed = False
        db_table = 'ANNEE_UNIV'

    def __str__(self):
        return self.libelle


class Cours(models.Model):
    id_cours = models.AutoField(primary_key=True, db_column='ID_COURS')
    code_cours = models.CharField(max_length=20, db_column='CODE_COURS')
    intitule = models.CharField(max_length=200, db_column='INTITULE')
    coef = models.DecimalField(max_digits=4, decimal_places=2, db_column='COEF')
    nb_seances_prev = models.IntegerField(db_column='NB_SEANCES_PREV')

    class Meta:
        managed = False
        db_table = 'COURS'
        verbose_name_plural = 'cours'

    def __str__(self):
        return self.code_cours


class Etudiant(models.Model):
    STATUTS = (
        ('ACTIF', 'Actif'),
        ('SUSPENDU', 'Suspendu'),
        ('DIPLOME', 'Diplômé'),
    )

    id_etudiant = models.AutoField(primary_key=True, db_column='ID_ETUDIANT')
    matricule = models.CharField(max_length=20, unique=True, db_column='MATRICULE')
    nom = models.CharField(max_length=80, db_column='NOM')
    prenom = models.CharField(max_length=80, db_column='PRENOM')
    email = models.CharField(
        max_length=120, unique=True, null=True, blank=True, db_column='EMAIL'
    )
    date_naissance = models.DateField(
        null=True, blank=True, db_column='DATE_NAISSANCE'
    )
    id_filiere = models.ForeignKey(
        Filiere, models.DO_NOTHING, db_column='ID_FILIERE'
    )
    statut = models.CharField(
        max_length=20, db_column='STATUT', choices=STATUTS, default='ACTIF'
    )

    class Meta:
        managed = False
        db_table = 'ETUDIANT'

    def __str__(self):
        return f'{self.prenom} {self.nom} ({self.matricule})'


class Inscription(models.Model):
    STATUTS = (('VALIDEE', 'Validée'), ('ANNULEE', 'Annulée'))

    id_inscription = models.AutoField(primary_key=True, db_column='ID_INSCRIPTION')
    id_etudiant = models.ForeignKey(
        Etudiant, models.DO_NOTHING, db_column='ID_ETUDIANT'
    )
    id_cours = models.ForeignKey(Cours, models.DO_NOTHING, db_column='ID_COURS')
    id_annee = models.ForeignKey(AnneeUniv, models.DO_NOTHING, db_column='ID_ANNEE')
    date_insc = models.DateField(db_column='DATE_INSC')
    statut_insc = models.CharField(
        max_length=20, db_column='STATUT_INSC', choices=STATUTS, default='VALIDEE'
    )

    class Meta:
        managed = False
        db_table = 'INSCRIPTION'

    def __str__(self):
        return f'Inscription {self.pk}'


class Seance(models.Model):
    STATUTS = (
        ('PREVUE', 'Prévue'),
        ('REALISEE', 'Réalisée'),
        ('ANNULEE', 'Annulée'),
    )

    id_seance = models.AutoField(primary_key=True, db_column='ID_SEANCE')
    id_cours = models.ForeignKey(Cours, models.DO_NOTHING, db_column='ID_COURS')
    id_annee = models.ForeignKey(AnneeUniv, models.DO_NOTHING, db_column='ID_ANNEE')
    date_seance = models.DateField(db_column='DATE_SEANCE')
    heure_debut = models.DecimalField(max_digits=4, decimal_places=2, db_column='HEURE_DEBUT')
    heure_fin = models.DecimalField(max_digits=4, decimal_places=2, db_column='HEURE_FIN')
    statut_seance = models.CharField(
        max_length=20, db_column='STATUT_SEANCE', choices=STATUTS, default='PREVUE'
    )

    class Meta:
        managed = False
        db_table = 'SEANCE'

    def __str__(self):
        return f'Séance {self.pk} — {self.date_seance}'


class ParamGlobalAnnee(models.Model):
    id_annee = models.OneToOneField(
        AnneeUniv,
        models.DO_NOTHING,
        db_column='ID_ANNEE',
        primary_key=True,
    )
    seuil_non_justif = models.IntegerField(db_column='SEUIL_NON_JUSTIF')

    class Meta:
        managed = False
        db_table = 'PARAM_GLOBAL_ANNEE'

    def __str__(self):
        return f'Seuil global ({self.id_annee_id})'


class ParamCoursSeuil(models.Model):
    id_param = models.AutoField(primary_key=True, db_column='ID_PARAM')
    id_cours = models.ForeignKey(Cours, models.DO_NOTHING, db_column='ID_COURS')
    id_annee = models.ForeignKey(AnneeUniv, models.DO_NOTHING, db_column='ID_ANNEE')
    seuil_non_justif = models.IntegerField(db_column='SEUIL_NON_JUSTIF')

    class Meta:
        managed = False
        db_table = 'PARAM_COURS_SEUIL'

    def __str__(self):
        return f'Seuil cours {self.id_cours_id} / année {self.id_annee_id}'


class Absence(models.Model):
    id_absence = models.AutoField(primary_key=True, db_column='ID_ABSENCE')
    id_inscription = models.ForeignKey(
        Inscription, models.DO_NOTHING, db_column='ID_INSCRIPTION'
    )
    id_seance = models.ForeignKey(Seance, models.DO_NOTHING, db_column='ID_SEANCE')
    motif = models.CharField(max_length=300, blank=True, null=True, db_column='MOTIF')
    justifiee = models.CharField(max_length=1, db_column='JUSTIFIEE', default='N')
    date_saisie = models.DateTimeField(db_column='DATE_SAISIE')

    class Meta:
        managed = False
        db_table = 'ABSENCE'

    def __str__(self):
        return f'Absence {self.pk}'


class HistoriqueAlerte(models.Model):
    id_alerte = models.AutoField(primary_key=True, db_column='ID_ALERTE')
    id_etudiant = models.ForeignKey(
        Etudiant, models.DO_NOTHING, db_column='ID_ETUDIANT'
    )
    id_cours = models.ForeignKey(Cours, models.DO_NOTHING, db_column='ID_COURS')
    id_annee = models.ForeignKey(AnneeUniv, models.DO_NOTHING, db_column='ID_ANNEE')
    nb_abs_non_just = models.IntegerField(db_column='NB_ABS_NON_JUST')
    date_alerte = models.DateTimeField(db_column='DATE_ALERTE')
    message = models.CharField(max_length=500, db_column='MESSAGE')

    class Meta:
        managed = False
        db_table = 'HISTORIQUE_ALERTE'

    def __str__(self):
        return f'Alerte {self.pk}'


class ProfilEtudiant(models.Model):
    """
    Compte de connexion (Django User) ↔ fiche ETUDIANT en base.
    Les mots de passe et droits restent entièrement côté Django (AUTH_USER).
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil_etudiant',
    )
    etudiant = models.OneToOneField(
        Etudiant,
        on_delete=models.PROTECT,
        related_name='profil_compte',
    )

    class Meta:
        db_table = 'LIEN_COMPTE_ETUDIANT'

    def __str__(self):
        return f'{self.user.username} → étudiant {self.etudiant_id}'


class NotificationApp(models.Model):
    """
    Notifications in-app (Django uniquement).
    Ex. informer la scolarité lorsqu’une absence est saisie par un enseignant.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications_app',
    )
    titre = models.CharField(max_length=200)
    corps = models.TextField()
    lu = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_envoi']
        verbose_name = 'notification'
        verbose_name_plural = 'notifications applicatives'

    def __str__(self):
        return self.titre


class ProfilApp(models.Model):
    """
    Profil applicatif Django (tous rôles) : affichage et coordonnées.
    Les droits d’accès restent portés par les groupes / permissions Django.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profil_app',
    )
    nom_affiche = models.CharField(
        max_length=120,
        blank=True,
        help_text='Nom affiché dans l’interface (optionnel).',
    )
    telephone = models.CharField(max_length=30, blank=True)

    class Meta:
        db_table = 'ABSENCE_PROFIL_APP'
        verbose_name = 'profil utilisateur'
        verbose_name_plural = 'profils utilisateurs'

    def __str__(self):
        return self.nom_affiche or self.user.get_username()


class SeuilAlerteEmailEnvoye(models.Model):
    """
    Une ligne par alerte HISTORIQUE_ALERTE pour laquelle l’e-mail seuil a été envoyé.
    Permet d’envoyer l’e-mail même si la notification in-app existait déjà.
    """

    historique_alerte_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text='PK de HISTORIQUE_ALERTE (Oracle / SQLite).',
    )
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ABSENCE_SEUIL_EMAIL_ENVOYE'
        verbose_name = 'envoi e-mail seuil'
        verbose_name_plural = 'envois e-mails seuil'

    def __str__(self):
        return f'Alerte #{self.historique_alerte_id}'

