from __future__ import absolute_import

import os
import gzip
from celery import Celery
from django.core.mail import EmailMessage, get_connection
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tryit.settings')

broker_url = 'mongodb://localhost:27017/celery'
backend = 'mongodb'

app = Celery('tryit', broker=broker_url, backend=backend)


# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


# @app.task(queue="mails")
@app.task
def send_mail(subject, message, from_addr, user_list, kwargs={}):
    for user in user_list:
        mail = EmailMessage(subject, message, from_email=from_addr, to=[from_addr, user.email],
                            connection=get_connection(), **kwargs)
        mail.send()
    return True


@app.task
def add_log(content, file_name):
    path = os.path.join(settings.SAVE_LOGS_DIR)
    if not os.path.exists(path):
        os.mkdir(path)
    name = os.path.join(path, file_name)
    with gzip.open(name, 'wb') as f:
        f.write(content)
    return True


if __name__ == '__main__':
    app.start()
