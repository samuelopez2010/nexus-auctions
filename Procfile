web: gunicorn nexus_core.wsgi --log-file -
worker: celery -A nexus_core worker -l info -P solo -B --max-tasks-per-child=10
