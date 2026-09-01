#!/bin/bash
set -e

REPORT="tests/performance/idle_baseline_report.txt"
echo "=== PHASE 20 IDLE BASELINE REPORT ===" > $REPORT
date >> $REPORT
echo "" >> $REPORT

echo "--- 1. Host Resources ---" >> $REPORT
free -m >> $REPORT
echo "" >> $REPORT
top -b -n 1 | head -n 10 >> $REPORT
echo "" >> $REPORT

echo "--- 2. Container Resources (Test vs Prod) ---" >> $REPORT
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

echo "--- 5. API Baseline Latency (Test Ingress) ---" >> $REPORT
curl -k -s -w "\nHTTP_CODE: %{http_code}\nTIME_TOTAL: %{time_total}s\nTIME_NAMELOOKUP: %{time_namelookup}s\nTIME_CONNECT: %{time_connect}s\nTIME_PRETRANSFER: %{time_pretransfer}s\nTIME_STARTTRANSFER: %{time_starttransfer}s\n" -o /dev/null https://localhost:8443/api/v1/baas/projects/ >> $REPORT
echo "" >> $REPORT

echo "--- 6. OOM Evidence (dmesg) ---" >> $REPORT
sudo dmesg -T | grep -i oom || echo "No OOM events found." >> $REPORT
echo "" >> $REPORT

echo "Baseline collection complete."
cat $REPORT
