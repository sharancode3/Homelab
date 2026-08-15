#!/bin/bash
set -e

echo "=== PHASE 20 10-PROJECT LOAD STAGE ==="

echo "Starting monitor in background..."
.venv/bin/python tests/performance/monitor.py 70 > tests/performance/monitor_10.log 2>&1 &
MONITOR_PID=$!

echo "Starting load test for 10 projects..."
.venv/bin/python tests/performance/load_test.py 10 > tests/performance/10_project_report.txt 2>&1
echo "Load test finished. Waiting for monitor to finish..."

wait $MONITOR_PID || echo "Monitor exited with error (Hard Abort?)"

echo "=== LOAD STAGE COMPLETE ==="
echo "Generating Final Metric Snapshot..."

REPORT="tests/performance/10_project_metrics.txt"
date > $REPORT
echo "--- 1. Host Resources ---" >> $REPORT
free -m >> $REPORT
echo "" >> $REPORT
top -b -n 1 | head -n 10 >> $REPORT
echo "" >> $REPORT

echo "--- 2. Container Resources ---" >> $REPORT
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}" | grep -E "homelab|NAME" >> $REPORT
echo "" >> $REPORT

echo "--- 3. Container States and Restart Counts ---" >> $REPORT
docker ps -a --filter "name=homelab" --format "table {{.Names}}\t{{.Status}}\t{{.State}}" >> $REPORT
echo "" >> $REPORT

echo "--- 4. Storage Sizes ---" >> $REPORT
echo "Test SQLite Volume (phase20test_platform_data_test):" >> $REPORT
docker run --rm -v phase20test_platform_data_test:/data alpine du -sh /data >> $REPORT 2>/dev/null || echo "Volume empty or not found" >> $REPORT
echo "Test MinIO Volume (phase20test_minio_data_test):" >> $REPORT
docker run --rm -v phase20test_minio_data_test:/data alpine du -sh /data >> $REPORT 2>/dev/null || echo "Volume empty or not found" >> $REPORT
echo "" >> $REPORT

echo "--- 5. SQLite Locked Events ---" >> $REPORT
docker logs homelab-auth-test 2>&1 | grep -i "database is locked" | wc -l >> $REPORT || echo "0" >> $REPORT
echo "" >> $REPORT

echo "--- 6. OOM Evidence (dmesg) ---" >> $REPORT
dmesg -T | grep -i oom || echo "No OOM events found." >> $REPORT
echo "" >> $REPORT

echo "Done."
