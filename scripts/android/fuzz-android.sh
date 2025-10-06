#!/bin/bash

# Usage: COMPOSE=path/to/docker-compose.yaml ./scripts/android/fuzz-android.sh
# Or modify the COMPOSE variable in this script.
# **WARNING:** Ensure that the DEVICE and SERVADDR environment variables in the docker-compose file are set correctly and do not conflict with other services.

set -e

COMPOSE=${COMPOSE:-""}
PROFILES=${PROFILES:-""}

if [[ -z "$COMPOSE" || -z "$PROFILES" ]]; then
    echo "Usage: COMPOSE=/path/to/docker-compose.yaml PROFILES=fuzzer1,fuzzer2,... $0"
    echo "Or modify COMPOSE and PROFILES variables in $0."
    exit 1
fi

# Split $PROFILES by comma and add --profile before each profile name.
PROFILES_ARR=(${PROFILES//,/ })
FUZZER_PROFILES=""
for profile in "${PROFILES_ARR[@]}"; do
    FUZZER_PROFILES+=" --profile $profile"
done

docker compose -f $COMPOSE --profile cvd-for-fuzz up -d
docker compose -f $COMPOSE $FUZZER_PROFILES up -d --timeout 86400

EXEC_TIME=0
while [ $EXEC_TIME -lt 86400 ]; do
    sleep 180s
    EXEC_TIME=$((EXEC_TIME + 180))
    echo ========== EXEC_TIME: $EXEC_TIME ==========
    if [[ $((EXEC_TIME % 10800)) -eq 0 || $(docker ps | grep cvd-for-fuzz | wc -l) -lt 1 ]]; then
        docker compose -f $COMPOSE --profile cvd-for-fuzz down
        docker compose -f $COMPOSE --profile cvd-for-fuzz up -d
    fi
    for port in {6520..6529}; do
        adb connect 0.0.0.0:$port
    done
done

docker compose -f $COMPOSE --profile cvd-for-fuzz $FUZZER_PROFILES down
