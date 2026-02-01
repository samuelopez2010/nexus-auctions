web: /bin/bash start.sh
worker: celery -A nexus_core worker -l info -P solo -B --max-tasks-per-child=10
