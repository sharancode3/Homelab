import asyncio
import httpx
import time
import logging
import statistics
import sys
from collections import Counter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://localhost:8443"  # Caddy ingress

class LoadTestConfig:
    def __init__(self, target_projects: int, duration_sec: int, rps: int, concurrent_workflows: int):
        self.target_projects = target_projects
        self.duration_sec = duration_sec
        self.rps = rps
        self.concurrent_workflows = concurrent_workflows

class LoadTester:
    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.client = httpx.AsyncClient(base_url=BASE_URL, verify=False, timeout=30.0)
        self.token = None
        self.project_ids = []
        self.latencies = []
        self.status_codes = Counter()
        self.errors = Counter()
        self.test_email = "phase20_tester@example.com"
        self.test_password = "SecureTestPassword123!"

    async def setup(self):
        resp = await self.client.post("/api/v1/auth/login", json={
            "email": self.test_email,
            "password": self.test_password
        })
        if resp.status_code == 401 or resp.status_code == 404:
            resp = await self.client.post("/api/v1/auth/register", json={
                "username": "phase20_tester",
                "email": self.test_email,
                "password": self.test_password
            })
            resp.raise_for_status()
            resp = await self.client.post("/api/v1/auth/login", json={
                "email": self.test_email,
                "password": self.test_password
            })
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    async def teardown(self):
        await self.client.aclose()

    async def provision_projects(self):
        logger.info(f"Provisioning up to {self.config.target_projects} projects...")
        resp = await self.client.get("/api/v1/baas/projects/")
        resp.raise_for_status()
        data = resp.json(); existing = data if isinstance(data, list) else data.get("projects", [])
        self.project_ids = [p["project_id"] for p in existing if p["project_name"].startswith("P20 Test")]

        needed = self.config.target_projects - len(self.project_ids)
        for i in range(needed):
            start = time.time()
            resp = await self.client.post("/api/v1/baas/projects/", json={
                "project_name": f"P20 Test {len(self.project_ids) + 1}",
                "project_slug": f"p20-test-{len(self.project_ids) + 1}"
            })
            self._record_metric(resp, start)
            if resp.status_code in (200, 201):
                self.project_ids.append(resp.json()["project_id"])
            elif resp.status_code == 403:
                logger.error("Hit project creation limit.")
                break

    def _record_metric(self, response: httpx.Response, start_time: float):
        latency = (time.time() - start_time) * 1000
        self.latencies.append(latency)
        self.status_codes[response.status_code] += 1
        if response.status_code >= 500:
            self.errors[f"HTTP_{response.status_code}"] += 1

    def _record_exception(self, e: Exception):
        self.errors[type(e).__name__] += 1
        self.status_codes[500] += 1

    async def workflow(self, project_id: str):
        start = time.time()
        try:
            resp = await self.client.get(f"/api/v1/baas/projects/{project_id}/tables")
            self._record_metric(resp, start)
            if resp.status_code == 200:
                data = resp.json()
                tables = data if isinstance(data, list) else data.get("tables", [])
                if not tables:
                    start_write = time.time()
                    resp_write = await self.client.post(f"/api/v1/baas/projects/{project_id}/tables", json={
                        "table_name": "test_table",
                        "schema": {"columns": [{"name": "val", "type": "string"}]}
                    })
                    self._record_metric(resp_write, start_write)
                else:
                    start_write = time.time()
                    resp_write = await self.client.post(f"/api/v1/baas/projects/{project_id}/data/test_table", json={
                        "data": {"val": f"test_{time.time()}"}
                    })
                    self._record_metric(resp_write, start_write)
        except Exception as e:
            self._record_exception(e)

    async def run_load(self):
        if self.config.target_projects == 0:
            logger.info("Target projects is 0 (Idle Baseline). Skipping concurrent workflow.")
            await asyncio.sleep(self.config.duration_sec)
            return

        logger.info(f"Starting load test: {self.config.duration_sec}s, {self.config.concurrent_workflows} workers, targeting {self.config.rps} RPS")
        start_time = time.time()
        
        async def worker():
            while time.time() - start_time < self.config.duration_sec:
                if not self.project_ids:
                    await asyncio.sleep(1)
                    continue
                pid = self.project_ids[int(time.time() * 1000) % len(self.project_ids)]
                await self.workflow(pid)
                await asyncio.sleep(self.config.concurrent_workflows / self.config.rps)

        workers = [asyncio.create_task(worker()) for _ in range(self.config.concurrent_workflows)]
        await asyncio.gather(*workers)

    def print_report(self):
        total_requests = len(self.latencies)
        logger.info("=== LOAD TEST REPORT ===")
        logger.info(f"Target Projects: {self.config.target_projects} | Provisioned: {len(self.project_ids)}")
        if total_requests == 0:
            logger.info("No requests recorded (Idle Baseline or failure).")
            return

        p50 = statistics.median(self.latencies)
        p95 = statistics.quantiles(self.latencies, n=100)[94] if total_requests >= 100 else max(self.latencies)
        p99 = statistics.quantiles(self.latencies, n=100)[98] if total_requests >= 100 else max(self.latencies)
        
        logger.info(f"Total Requests: {total_requests}")
        logger.info(f"Latency (ms): p50={p50:.2f}, p95={p95:.2f}, p99={p99:.2f}")
        logger.info(f"Status Codes: {dict(self.status_codes)}")
        logger.info(f"Errors: {dict(self.errors)}")
        
        error_rate = (sum(self.errors.values()) / total_requests) * 100
        logger.info(f"Error Rate: {error_rate:.2f}%")
        if error_rate > 5.0:
            logger.warning("SAFETY ABORT TRIGGER: Error rate > 5%. Evaluate system limits.")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python load_test.py <target_projects>")
        sys.exit(1)
    
    target_projects = int(sys.argv[1])
    config = LoadTestConfig(target_projects=target_projects, duration_sec=60, rps=20, concurrent_workflows=10)
    
    tester = LoadTester(config)
    await tester.setup()
    await tester.provision_projects()
    await tester.run_load()
    tester.print_report()
    await tester.teardown()

if __name__ == "__main__":
    asyncio.run(main())
