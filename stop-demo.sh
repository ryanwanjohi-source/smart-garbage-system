#!/usr/bin/env bash
# Stop everything started by ./demo.sh.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ -f .demo_pids ]]; then
  while read -r pid; do
    if kill "$pid" 2>/dev/null; then
      echo "Stopped pid $pid"
    fi
  done < .demo_pids
  rm -f .demo_pids
else
  echo "No .demo_pids file — nothing started by demo.sh is tracked."
fi

if [[ -f .demo_mosq_owned ]] && [[ "$(cat .demo_mosq_owned)" == "1" ]]; then
  if pkill -x mosquitto 2>/dev/null; then
    echo "Stopped Mosquitto (it was started by demo.sh)."
  fi
  rm -f .demo_mosq_owned
fi

echo "Demo stopped."
