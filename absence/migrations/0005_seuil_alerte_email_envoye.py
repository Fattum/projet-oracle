# Table de traçage : e-mail seuil envoyé une fois par HISTORIQUE_ALERTE

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0004_profil_app'),
    ]

    operations = [
        migrations.CreateModel(
            name='SeuilAlerteEmailEnvoye',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('historique_alerte_id', models.IntegerField(db_index=True, help_text='PK de HISTORIQUE_ALERTE (Oracle / SQLite).', unique=True)),
                ('date_envoi', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'envoi e-mail seuil',
                'verbose_name_plural': 'envois e-mails seuil',
                'db_table': 'ABSENCE_SEUIL_EMAIL_ENVOYE',
            },
        ),
    ]
