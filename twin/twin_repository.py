"""twin/twin_repository.py — Stores twin records durably."""
from __future__ import annotations
from storage.repository_base import RepositoryBase

class TwinDecisionMomentRepository(RepositoryBase): pass
class TwinRecommendationRepository(RepositoryBase): pass
class TwinActionRepository(RepositoryBase): pass
class TwinCounterfactualRepository(RepositoryBase): pass
class TwinReconciliationRepository(RepositoryBase): pass
