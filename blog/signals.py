from django.dispatch import receiver, Signal
from django.db.models.signals import post_save, m2m_changed
from blog.models import Article, MailTemplate
from tryit.celery import send_mail, add_log

send_published = Signal(providing_args=["subscribers", "title", "description"])
send2subscriber = Signal(providing_args=["subscriber", "title", "description"])


@receiver(post_save, sender=Article)
def article_published(sender, **kwargs):
    created = kwargs.get('created')
    instance = kwargs.get('instance')
    if created and instance.is_published():
        template = MailTemplate.objects.get(default=True)
        send_mail(template.subject, template.message, template.from_addr,
                  instance.subscribers)
