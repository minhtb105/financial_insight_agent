"""
Memory architecture for the financial insight agent.

Implements a 3-tier memory system for context retention and learning:
- Short-term: Redis-based fast access (2h TTL)
- Episodic: PostgreSQL with pgvector for semantic search
- Long-term: PostgreSQL for persistent knowledge storage
"""

from .short_term.memory import ShortTermMemory
from .episodic.memory import EpisodicMemory
from .long_term.memory import LongTermMemory
from .memory_manager import MemoryManager

__all__ = [
    'ShortTermMemory',
    'EpisodicMemory', 
    'LongTermMemory',
    'MemoryManager'
]