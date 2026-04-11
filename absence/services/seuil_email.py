"""
Envoi d'e-mails lors du franchissement du seuil d'absences non justifiées.
Activé uniquement si EMAIL_HOST, EMAIL_USER et EMAIL_PASS sont définis (.env).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def emails_seuil_actifs():
    return getattr(settings, 'SEUIL_EMAIL_ENABLED', False)


def envoyer_emails_alerte_seuil(titre, corps_texte, etudiant=None):
    """
    Notifie l'admin (ADMIN_EMAIL) et, si présent, l'e-mail de l'étudiant.
    `corps_texte` : message sans marqueur HTML (même contenu que l'alerte).

    Retourne True si au moins un message a été accepté par le backend SMTP, False sinon.
    """
    if not emails_seuil_actifs():
        return False
    recipients = []
    admin = (getattr(settings, 'ADMIN_EMAIL', None) or '').strip()
    if admin:
        recipients.extend(
            e.strip() for e in admin.split(',') if e.strip()
        )
    if etudiant is not None:
        em = getattr(etudiant, 'email', None) or ''
        em = em.strip()
        if em and em not in recipients:
            recipients.append(em)
    if not recipients:
        logger.warning('Seuil e-mail : aucun destinataire (ADMIN_EMAIL vide ?).')
        return False
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(
        settings, 'EMAIL_HOST_USER', ''
    )
    if not from_email:
        logger.warning('Seuil e-mail : DEFAULT_FROM_EMAIL / EMAIL_USER absent.')
        return False
    body = corps_texte[:4000]
    if etudiant is not None:
        nom = (
            f"{getattr(etudiant, 'prenom', '')} {getattr(etudiant, 'nom', '')}".strip()
        )
        mat = getattr(etudiant, 'matricule', '') or ''
        if nom or mat:
            entete = f"Étudiant : {nom}"
            if mat:
                entete = f"{entete} — {mat}"
            body = f"{entete}\n\n{body}"
    try:
        n = send_mail(
            subject=titre[:200],
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
        if n:
            logger.info(
                'E-mail alerte seuil envoyé à %s (sujet: %s)',
                recipients,
                titre[:80],
            )
        return bool(n)
    except Exception:
        logger.exception(
            'Échec envoi e-mail alerte seuil (vérifiez SMTP / Gmail : '
            'mot de passe d’application, etc.)'
        )
        return False
