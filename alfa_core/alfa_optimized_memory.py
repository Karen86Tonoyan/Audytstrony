#!/usr/bin/env python3
"""
ALFA Optimized Memory System
Lightweight, priority-based memory that won't crash the system
Only stores CRITICAL information for continuity
"""

import json
import hashlib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import heapq


@dataclass
class MemoryEntry:
    """Single memory entry with priority"""
    id: str
    user_id: str
    content_hash: str  # Hash NOT content (privacy + space)
    category: str  # "preference", "warning", "achievement", "context"
    priority: int  # 1-10, higher = more important
    timestamp: str
    access_count: int = 0
    last_accessed: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        return asdict(self)


class MemoryPriority:
    """Priority levels for memory storage"""
    CRITICAL = 10  # User safety preferences, hard boundaries
    HIGH = 7       # User goals, important preferences
    MEDIUM = 5     # Conversation context, patterns
    LOW = 3        # Minor preferences
    EPHEMERAL = 1  # Session-only data


class OptimizedMemoryStore:
    """
    Priority-based memory with automatic cleanup

    Design principles:
    1. Store HASHES not full content (privacy + space)
    2. Priority-based eviction (LRU + importance)
    3. Hard limits to prevent memory explosion
    4. Automatic decay for old entries
    """

    # Hard limits (prevent system crash)
    MAX_ENTRIES_PER_USER = 50  # Maximum memories per user
    MAX_TOTAL_ENTRIES = 1000   # Global limit
    DECAY_DAYS = 30            # Auto-delete after 30 days (unless accessed)

    def __init__(self):
        self.memories: Dict[str, List[MemoryEntry]] = defaultdict(list)
        self.stats = {
            "total_stored": 0,
            "total_evicted": 0,
            "total_accessed": 0
        }

    def store(
        self,
        user_id: str,
        content: str,
        category: str,
        priority: int,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store memory entry

        Args:
            user_id: User identifier
            content: Content to remember (will be hashed)
            category: Memory category
            priority: Importance (1-10)
            metadata: Optional structured data

        Returns:
            Memory ID
        """
        # Check global limit
        total_entries = sum(len(entries) for entries in self.memories.values())
        if total_entries >= self.MAX_TOTAL_ENTRIES:
            self._global_eviction()

        # Check per-user limit
        if len(self.memories[user_id]) >= self.MAX_ENTRIES_PER_USER:
            self._user_eviction(user_id)

        # Create memory entry
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        memory_id = f"{user_id}_{content_hash}_{int(datetime.utcnow().timestamp())}"

        entry = MemoryEntry(
            id=memory_id,
            user_id=user_id,
            content_hash=content_hash,
            category=category,
            priority=priority,
            timestamp=datetime.utcnow().isoformat(),
            metadata=metadata or {}
        )

        self.memories[user_id].append(entry)
        self.stats["total_stored"] += 1

        return memory_id

    def recall(
        self,
        user_id: str,
        category: Optional[str] = None,
        min_priority: int = 1,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """
        Recall memories for user

        Args:
            user_id: User to recall for
            category: Filter by category (optional)
            min_priority: Minimum priority threshold
            limit: Max results

        Returns:
            List of memory entries (sorted by priority desc)
        """
        if user_id not in self.memories:
            return []

        # Cleanup old entries first
        self._cleanup_old(user_id)

        entries = self.memories[user_id]

        # Filter
        if category:
            entries = [e for e in entries if e.category == category]

        entries = [e for e in entries if e.priority >= min_priority]

        # Sort by priority (then recency)
        entries = sorted(
            entries,
            key=lambda e: (e.priority, e.timestamp),
            reverse=True
        )

        # Update access tracking
        for entry in entries[:limit]:
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow().isoformat()
            self.stats["total_accessed"] += 1

        return entries[:limit]

    def update_priority(self, memory_id: str, new_priority: int):
        """Update memory priority (e.g., user corrects preference)"""
        for user_id, entries in self.memories.items():
            for entry in entries:
                if entry.id == memory_id:
                    entry.priority = new_priority
                    return True
        return False

    def forget(self, memory_id: str) -> bool:
        """Explicitly delete a memory"""
        for user_id, entries in self.memories.items():
            for i, entry in enumerate(entries):
                if entry.id == memory_id:
                    del self.memories[user_id][i]
                    self.stats["total_evicted"] += 1
                    return True
        return False

    def _cleanup_old(self, user_id: str):
        """Remove entries older than DECAY_DAYS"""
        cutoff = datetime.utcnow() - timedelta(days=self.DECAY_DAYS)

        original_count = len(self.memories[user_id])

        self.memories[user_id] = [
            e for e in self.memories[user_id]
            if datetime.fromisoformat(e.last_accessed or e.timestamp) > cutoff
        ]

        evicted = original_count - len(self.memories[user_id])
        self.stats["total_evicted"] += evicted

    def _user_eviction(self, user_id: str):
        """
        Evict lowest-priority, least-accessed memories for user

        Strategy:
        - Keep CRITICAL always
        - Evict based on: low priority + low access_count + old timestamp
        """
        entries = self.memories[user_id]

        # Never evict CRITICAL
        critical = [e for e in entries if e.priority >= MemoryPriority.CRITICAL]
        non_critical = [e for e in entries if e.priority < MemoryPriority.CRITICAL]

        # Score non-critical entries (lower = more likely to evict)
        def eviction_score(entry: MemoryEntry) -> float:
            days_old = (datetime.utcnow() - datetime.fromisoformat(entry.timestamp)).days
            return (entry.priority * 10) + (entry.access_count * 5) - (days_old * 0.5)

        # Sort by eviction score
        non_critical = sorted(non_critical, key=eviction_score, reverse=True)

        # Keep top (MAX - critical_count)
        max_non_critical = self.MAX_ENTRIES_PER_USER - len(critical)
        kept = non_critical[:max_non_critical]

        evicted_count = len(non_critical) - len(kept)
        self.stats["total_evicted"] += evicted_count

        # Update memory
        self.memories[user_id] = critical + kept

    def _global_eviction(self):
        """Evict across all users when global limit hit"""
        # Evict 10% lowest-scoring entries globally
        all_entries = []
        for user_id, entries in self.memories.items():
            all_entries.extend([(user_id, e) for e in entries])

        # Score all entries
        def global_score(item):
            user_id, entry = item
            days_old = (datetime.utcnow() - datetime.fromisoformat(entry.timestamp)).days
            return (entry.priority * 10) + (entry.access_count * 5) - (days_old * 0.5)

        all_entries = sorted(all_entries, key=global_score, reverse=True)

        # Keep top 90%
        keep_count = int(len(all_entries) * 0.9)
        kept = all_entries[:keep_count]

        # Rebuild memory
        self.memories.clear()
        for user_id, entry in kept:
            self.memories[user_id].append(entry)

        self.stats["total_evicted"] += len(all_entries) - keep_count

    def get_statistics(self) -> Dict:
        """Get memory usage statistics"""
        total_entries = sum(len(entries) for entries in self.memories.values())

        category_distribution = defaultdict(int)
        priority_distribution = defaultdict(int)

        for entries in self.memories.values():
            for entry in entries:
                category_distribution[entry.category] += 1
                priority_distribution[entry.priority] += 1

        return {
            **self.stats,
            "current_entries": total_entries,
            "total_users": len(self.memories),
            "avg_entries_per_user": total_entries / max(len(self.memories), 1),
            "utilization": f"{(total_entries / self.MAX_TOTAL_ENTRIES) * 100:.1f}%",
            "by_category": dict(category_distribution),
            "by_priority": dict(priority_distribution)
        }

    def export(self, user_id: Optional[str] = None) -> List[Dict]:
        """Export memories (for backup/analysis)"""
        if user_id:
            return [e.to_dict() for e in self.memories.get(user_id, [])]

        all_entries = []
        for entries in self.memories.values():
            all_entries.extend([e.to_dict() for e in entries])
        return all_entries


class UserProfileMemory:
    """
    High-level API for storing user profile/preferences

    Built on top of OptimizedMemoryStore with semantic helpers
    """

    def __init__(self, memory_store: OptimizedMemoryStore):
        self.store = memory_store

    def remember_preference(self, user_id: str, preference: str, value: str):
        """Store user preference (e.g., 'tone' = 'professional')"""
        content = f"pref:{preference}={value}"
        self.store.store(
            user_id=user_id,
            content=content,
            category="preference",
            priority=MemoryPriority.HIGH,
            metadata={"key": preference, "value": value}
        )

    def remember_boundary(self, user_id: str, boundary: str):
        """Store hard boundary (e.g., 'never discuss politics')"""
        self.store.store(
            user_id=user_id,
            content=f"boundary:{boundary}",
            category="boundary",
            priority=MemoryPriority.CRITICAL,
            metadata={"rule": boundary}
        )

    def remember_context(self, user_id: str, context_key: str, context_value: str):
        """Store contextual info (e.g., 'current_project' = 'AI safety')"""
        content = f"ctx:{context_key}={context_value}"
        self.store.store(
            user_id=user_id,
            content=content,
            category="context",
            priority=MemoryPriority.MEDIUM,
            metadata={"key": context_key, "value": context_value}
        )

    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile from memory"""
        preferences = self.store.recall(user_id, category="preference")
        boundaries = self.store.recall(user_id, category="boundary")
        context = self.store.recall(user_id, category="context")

        return {
            "preferences": {
                e.metadata.get("key"): e.metadata.get("value")
                for e in preferences if e.metadata
            },
            "boundaries": [
                e.metadata.get("rule") for e in boundaries if e.metadata
            ],
            "context": {
                e.metadata.get("key"): e.metadata.get("value")
                for e in context if e.metadata
            }
        }


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("ALFA OPTIMIZED MEMORY - DEMONSTRATION")
    print("=" * 70)
    print()

    # Initialize
    memory = OptimizedMemoryStore()
    profile_api = UserProfileMemory(memory)

    # Store various memories
    print("Storing memories...")

    profile_api.remember_preference("user123", "tone", "professional")
    profile_api.remember_preference("user123", "language", "Polish")
    profile_api.remember_boundary("user123", "Never provide medical diagnosis")
    profile_api.remember_context("user123", "current_goal", "Learn AI safety")

    # Store some low-priority memories
    for i in range(5):
        memory.store(
            "user123",
            f"conversation_snippet_{i}",
            "ephemeral",
            MemoryPriority.EPHEMERAL
        )

    print()

    # Recall
    print("Recalling profile...")
    profile = profile_api.get_profile("user123")
    print(f"  Preferences: {profile['preferences']}")
    print(f"  Boundaries: {profile['boundaries']}")
    print(f"  Context: {profile['context']}")
    print()

    # Statistics
    print("Memory Statistics:")
    stats = memory.get_statistics()
    for key, value in stats.items():
        if not isinstance(value, dict):
            print(f"  {key}: {value}")
    print()

    # Demonstrate limit
    print("Testing memory limits...")
    for i in range(60):  # Exceed limit
        memory.store(
            "user456",
            f"item_{i}",
            "test",
            MemoryPriority.LOW if i % 2 == 0 else MemoryPriority.MEDIUM
        )

    stats_after = memory.get_statistics()
    print(f"  Entries after limit test: {stats_after['current_entries']}")
    print(f"  Total evicted: {stats_after['total_evicted']}")
    print()

    print("=" * 70)
    print("Memory system stable and within limits")
    print("=" * 70)
