"""storage/storage_router.py — Routes objects into correct repositories with environment context."""
from __future__ import annotations
from typing import Any

class StorageRouter:
    def __init__(self, repositories: dict[str,Any]):
        self.repos=repositories
    def _repo(self,name): return self.repos.get(name)
    def save_policy_version(self,r): self._repo("policy_versions") and self._repo("policy_versions").upsert(r["policy_version_id"],r)
    def save_change_request(self,r): self._repo("policy_change_requests") and self._repo("policy_change_requests").upsert(r["change_request_id"],r)
    def save_workflow_event(self,r): self._repo("workflow_events") and self._repo("workflow_events").insert(r["workflow_event_id"],r)
    def save_transition_journal(self,r): self._repo("transition_journals") and self._repo("transition_journals").upsert(r["journal_id"],r)
    def save_slippage_event(self,r): self._repo("slippage_events") and self._repo("slippage_events").insert(r["slippage_id"],r)
    def save_alert(self,r): self._repo("alerts") and self._repo("alerts").insert(r["alert_id"],r)
    def save_validation_run(self,r): self._repo("validation_runs") and self._repo("validation_runs").insert(r.get("validation_run_id","?"),r)
    def save_environment_state(self,k,r): self._repo("environment_runtime_state") and self._repo("environment_runtime_state").upsert(k,r)
