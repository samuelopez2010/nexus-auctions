web: gunicorn nexus_core.wsgi --log-file -
worker: celery -A nexus_core worker -l info -P eventlet
beat: celery -A nexus_core beat -l info
