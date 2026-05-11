#!/bin/bash

echo "check system status"
systemctl status app

echo "check app log"
journalctl -u app -f

echo " locally accessible"
curl http://localhost:8080/hello

echo "check listening port"
lsof -i -P -n | grep LISTEN

echo "check disk usage"
df -h

echo "=== Last 5 errors in app log ==="
grep "ERROR" ~/cloudlab/logs/app.log | tail -5

echo "=== Error count ==="
grep "ERROR" ~/cloudlab/logs/app.log | wc -l