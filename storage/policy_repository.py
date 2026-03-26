"""storage/policy_repository.py — Repository classes for policy repository."""
from __future__ import annotations
from storage.repository_base import RepositoryBase

class PolicyVersionRepository(RepositoryBase): pass
class PolicyChangeRequestRepository(RepositoryBase): pass
class ControlPlaneAuditRepository(RepositoryBase): pass
