# Generated manually for ProfilApp (profil Django tous rôles)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('absence', '0003_app_notifications_groups'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfilApp',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom_affiche', models.CharField(blank=True, help_text='Nom affiché dans l’interface (optionnel).', max_length=120)),
                ('telephone', models.CharField(blank=True, max_length=30)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profil_app', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'profil utilisateur',
                'verbose_name_plural': 'profils utilisateurs',
                'db_table': 'ABSENCE_PROFIL_APP',
            },
        ),
    ]
