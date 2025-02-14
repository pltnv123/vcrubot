import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vcru.settings')

app = Celery('vcru')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
