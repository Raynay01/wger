#!/bin/bash
# Healthy when clamd answers PING with PONG
exec 3<>/dev/tcp/127.0.0.1/3310 || exit 1
printf 'nPING\n' >&3
read -r -t 5 answer <&3
[ "$answer" = "PONG" ]
