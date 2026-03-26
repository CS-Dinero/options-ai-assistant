"""storage/journal_repository.py — Repository classes for journal repository."""
from __future__ import annotations
from storage.repository_base import RepositoryBase

class TransitionJournalRepository(RepositoryBase): pass
class TransitionOutcomeRepository(RepositoryBase): pass
class SlippageEventRepository(RepositoryBase): pass
