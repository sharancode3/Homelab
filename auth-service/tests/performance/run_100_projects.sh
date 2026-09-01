#!/bin/bash
set -e

echo "=== PHASE 20 100-PROJECT LOAD STAGE ==="

echo "Starting monitor in background..."
.venv/bin/python tests/performance/monitor.py 70 > tests/performance/monitor_100.log 2>&1 &
MONITOR_PID=$!

echo "Starting load test for 100 projects..."
.venv/bin/python tests/performance/load_test.py 100 > tests/performance/100_project_report.txt 2>&1 &
LOAD_PID=$!

set +e
wait -n -p FIRST_EXIT_PID $MONITOR_PID $LOAD_PID
FIRST_EXIT_CODE=$?
set -e

if [ "$FIRST_EXIT_PID" = "$MONITOR_PID" ]; then
    if [ $FIRST_EXIT_CODE -ne 0 ]; then
        echo "HARD SAFETY ABORT TRIGGERED: Monitor exited prematurely with code $FIRST_EXIT_CODE!"
        kill -9 $LOAD_PID 2>/dev/null || true
        exit 1
    else
        echo "ERROR: Monitor exited successfully but before the load test finished. This is unexpected."
        kill -9 $LOAD_PID 2>/dev/null || true
        exit 1
    fi
else
    # Load test exited first
    if [ $FIRST_EXIT_CODE -ne 0 ]; then
        echo "ERROR: Load test failed with code $FIRST_EXIT_CODE"
        kill -9 $MONITOR_PID 2>/dev/null || true
        exit $FIRST_EXIT_CODE
    fi
    echo "Load test finished successfully. Waiting for monitor to finish safely..."
    wait $MONITOR_PID || echo "Monitor finished with error (post-test)"
fi

echo "=== LOAD STAGE COMPLETE ==="
echo "Generating Final Metric Snapshot..."

REPORT="tests/performance/100_project_metrics.txt"
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
