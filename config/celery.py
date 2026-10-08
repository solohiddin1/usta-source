from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')
app.conf.enable_utc = False
app.conf.update(timezone='Asia/Tashkent')
# app.conf.broker_url = f"redis://localhost:6379/0"
app.conf.broker_url = f"redis://95.130.227.254:6379/0"
# app.conf.result_backend = f"redis://localhost:6379/0"
app.conf.result_backend = f"redis://95.130.227.254:6379/0"
app.conf.broker_connection_retry_on_startup = True
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')