# Phase 20 Performance Audit & Resource Quota Decision

## 1. Objective and Constraints
Phase 20 measures resource consumption and establishes evidence-based resource limits to protect the core platform against uncontrolled resource consumption. A critical constraint is the 4GB RAM boundary of the physical ThinkPad host, requiring explicit validation that limits are within hardware safety margins.

## 2. Testing Isolation Strategy
To prevent load generation from destabilizing the production `homelab` deployment or triggering false-positive alerts, all tests were strictly executed inside a dedicated `phase20test` Compose environment. This temporary test environment featured an isolated Docker network (`phase20test_default`), dedicated storage volumes, and a dedicated Caddy ingress routing solely to the test `auth-service`.

## 3. Progressive Testing Methodology
Testing was conducted using a progressive burst provisioning methodology to evaluate the platform scaling under stress:
- Idle Baseline validation
- 10-project burst
- 20-project burst
- 50-project burst
- 100-project burst peak boundary

## 4. Watchdog Defect and Correction
During the initial progression, a defect was identified in the test monitoring harness (`monitor.py`). The watchdog initially observed all restarting containers across the host instead of scoping strictly to the `phase20test` environment. This caused the pre-existing restart loop in the unrelated production `homelab-tunnel` container to instantly trigger the monitor's Hard Safety Abort.

Because the load generators were allowed to continue despite the watchdog exiting early, the original 10/20/50/100 tests proceeded without continuous active monitoring. Therefore, the original continuous-monitoring claims are methodologically incomplete. The test harness was subsequently corrected with strict scoping and robust process supervision.

## 5. Evidence Classification
- **Valid Original Measurements:** The original load-generator measurements (throughput, latency, 429 rate-limiting) remain valid where directly measured.
- **Invalidated Claims:** The original continuous watchdog/stability claims are invalid/incomplete due to the dead monitor.
- **Authoritative Evidence:** The corrected 100-project run provides the authoritative continuously supervised peak-boundary evidence, with no observed safety-threshold breach, container restart, or OOM event during the monitored execution.

## 6. Corrected 100-Project Results
The authoritative, continuously supervised 100-project load test yielded the following results:
- 100 projects
- 1,410 requests
- p50 84.50 ms
- p95 180.71 ms
- p99 407.23 ms
- 0 5xx
- 0 timeouts
- 0 SQLite lock events
- 0 OOM evidence
- 0 phase20test container restarts
- continuous monitor completed successfully
- auth-service-test ~54.30 MiB

## 7. Final Enforcement Decision
Based on the authoritative evidence, the following strict enforcement was implemented:
- auth-service memory limit = 256M
- no CPU limit
- no project quota
- no new SQLite quota
- no new MinIO quota
- no payload-limit change
- no rate-limit change
- no architecture change

## 8. Decisions NOT Made
Phase 20 explicitly does NOT introduce:
- CPU limit
- 100-project application quota
- SQLite/platform storage quota
- new MinIO quota
- new payload limit
- new API rate-limit configuration
- architecture refactor
- project deletion feature
- user deletion feature
- Python SDK implementation
- Phase 21 functionality

Existing limits that were already present are not represented as newly introduced Phase 20 limits.

## 9. Limitations
Phase 20 testing successfully validated the specific burst workload, but explicitly did NOT prove:
- maximum theoretical project capacity
- maximum unrestricted RPS
- heavy binary/MinIO workload capacity
- large payload capacity
- long-term memory leak behavior
- CPU exhaustion boundary
- maximum SQLite data-plane storage capacity

## 10. Known Anomalies
The production `homelab-tunnel` anomaly remains pre-existing and was intentionally excluded from Phase 20 watchdog scope.

## 11. Final Conclusion
The corrected 100-project campaign demonstrated stable operation under the observed workload and monitoring interval on the 4 GB ThinkPad, with no observed OOM, restart, SQLite locking, 5xx, or timeout failure.

The 256M auth-service memory limit is the only new resource enforcement justified by the Phase 20 evidence.

Phase 20 does not establish 100 projects as the absolute maximum system capacity.

## 12. Phase Status
Phase 20 implementation/testing is complete pending the formal Git staging, implementation commit, push, roadmap lock commit, and lock push.

Phase 21 has NOT started.
