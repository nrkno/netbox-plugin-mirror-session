#!/bin/bash
# Run the plugin's test suite in the official NetBox image. NETBOX_VERSION selects the image tag.
set -euo pipefail
cd "$(dirname "$0")"
status=0
docker compose -f docker-compose.yml -p netbox-mirror-session-tests run --rm netbox || status=$?
docker compose -f docker-compose.yml -p netbox-mirror-session-tests down --volumes --remove-orphans
exit "$status"
