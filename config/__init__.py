# Without this the Celery app is never created inside the Django process, so .delay()
# would fall back to the default app (amqp://localhost) and the task would never reach
# the Redis broker the worker listens on.
from .celery import app as celery_app

__all__ = ('celery_app',)
