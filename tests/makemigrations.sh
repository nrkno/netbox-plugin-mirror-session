#!/bin/bash
# Generate migrations for model changes in the official NetBox image and copy them into the working tree.
set -euo pipefail
cd "$(dirname "$0")"
status=0
docker compose -f docker-compose.yml -p netbox-mirror-session-migrations run --rm \
    -v "$(pwd)/../netbox_mirror_session/migrations:/out" \
    -v "$(pwd)/developer.py:/etc/netbox/config/developer.py:ro" \
    netbox "cp -r /plugin /tmp/plugin \
        && /usr/local/bin/uv pip install --quiet --python /opt/netbox/venv/bin/python -e /tmp/plugin \
        && cd /opt/netbox/netbox \
        && /opt/netbox/venv/bin/python manage.py makemigrations netbox_mirror_session \
        && cp -n /tmp/plugin/netbox_mirror_session/migrations/*.py /out/ \
        && chown $(id -u):$(id -g) /out/*.py" || status=$?
docker compose -f docker-compose.yml -p netbox-mirror-session-migrations down --volumes --remove-orphans
exit "$status"
