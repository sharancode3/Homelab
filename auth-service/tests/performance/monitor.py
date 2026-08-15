import os
import time
import subprocess
import json
import logging
import psutil

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def get_docker_stats():
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}"],
            capture_output=True,
            text=True,
            check=True
        )
        stats = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|")
            stats.append({"name": parts[0], "cpu": parts[1], "mem": parts[2]})
        return stats
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get docker stats: {e}")
        return []

def get_host_metrics():
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu = psutil.cpu_percent(interval=None)
    return {
        "ram_used_mb": vm.used / (1024 * 1024),
        "ram_avail_mb": vm.available / (1024 * 1024),
        "swap_used_mb": swap.used / (1024 * 1024),
        "cpu_percent": cpu
    }

def get_db_size():
    data_dir = "/var/lib/auth-service/data"
    if os.path.exists(data_dir):
        return sum(os.path.getsize(os.path.join(dirpath, filename))
                   for dirpath, _, filenames in os.walk(data_dir)
                   for filename in filenames) / (1024 * 1024)
    return 0.0

def check_safety_abort(host_metrics):
    if host_metrics["ram_avail_mb"] < 200:
        logger.error("HARD ABORT: Available RAM critically low (< 200MB).")
        return True
    try:
        restarts = subprocess.run(
            ["docker", "ps", "-q", "--filter", "status=restarting", "--filter", "label=com.docker.compose.project=phase20test"],
            capture_output=True, text=True
        )
        if restarts.stdout.strip():
            logger.error("HARD ABORT: Containers are restarting.")
            return True
            
        exited = subprocess.run(
            ["docker", "ps", "-q", "--filter", "status=exited", "--filter", "label=com.docker.compose.project=phase20test"],
            capture_output=True, text=True
        )
        if exited.stdout.strip():
            logger.error("HARD ABORT: Containers have crashed (Possible OOM).")
            return True
    except Exception:
        pass
    return False

def monitor_loop(duration_sec=60):
    start_time = time.time()
    logger.info(f"Starting monitoring loop for {duration_sec} seconds")
    report = []
    while time.time() - start_time < duration_sec:
        host = get_host_metrics()
        stats = get_docker_stats()
        db_size = get_db_size()
        snapshot = {
            "timestamp": time.time(),
            "host": host,
            "containers": stats,
            "db_size_mb": db_size
        }
        report.append(snapshot)
        logger.info(f"Host: CPU {host['cpu_percent']}% | RAM Avail {host['ram_avail_mb']:.1f}MB | Swap {host['swap_used_mb']:.1f}MB | DB {db_size:.1f}MB")
        if check_safety_abort(host):
            logger.error("Monitoring triggered Hard Safety Abort.")
            with open("monitor_abort.json", "w") as f:
                json.dump(snapshot, f)
            return False
        time.sleep(2)
    with open("monitor_report.json", "w") as f:
        json.dump(report, f)
    logger.info("Monitoring completed safely.")
    return True

if __name__ == "__main__":
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    success = monitor_loop(duration)
    if not success:
        sys.exit(1)
