#!/usr/bin/env bash
set -euo pipefail

ADDR1="192.168.100.2"
ADDR2="192.168.100.232"

INTERVAL=600
PING_COUNT=2
PING_TIMEOUT=10

LOGFILE="$HOME/ckinternal.log"

while true; do
  ts="$(date '+%Y-%m-%d %H:%M:%S')"

  status1="FAIL"
  status2="FAIL"

  if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$ADDR1" >/dev/null 2>&1; then
    status1="OK"
  fi

  if ping -c "$PING_COUNT" -W "$PING_TIMEOUT" "$ADDR2" >/dev/null 2>&1; then
    status2="OK"
  fi

  if [[ "$status1" != "OK" || "$status2" != "OK" ]]; then
    echo "$ts ADDR1=$ADDR1 status=$status1 ADDR2=$ADDR2 status=$status2" >> "$LOGFILE"

    notify_msg="[$ts] Ping failed. ADDR1=$ADDR1 ($status1), ADDR2=$ADDR2 ($status2)"

    if command -v notify-send >/dev/null 2>&1; then
      notify-send -u  critical "Ping check" "$notify_msg"
    elif command -v wall >/dev/null 2>&1; then
      wall "$notify_msg"
    else
      echo "$notify_msg"
    fi
  fi

  sleep "$INTERVAL"
done
