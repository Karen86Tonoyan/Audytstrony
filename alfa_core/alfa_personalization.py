#!/usr/bin/env python3
"""
ALFA Personalization Engine
Value-weighted preference learning WITHOUT emotional manipulation
Auditable, deterministic, cold-tech approach
"""

import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import defaultdict


@dataclass
class UserPreference:
    """Single user preference with confidence tracking"""
    key: str  # e.g., "tone", "verbosity", "domain_focus"
    value: str  # e.g., "professional", "concise", "security"
    confidence: float  # 0.0-1.0, based on # observations
    evidence_count: int  # How many times observed
    last_updated: str
    source: str  # "explicit" (user told us) vs "inferred" (detected)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PersonalizationProfile:
    """Complete user personalization profile"""
    user_id: str
    preferences: Dict[str, UserPreference]
    version: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['preferences'] = {
            k: v.to_dict() for k, v in self.preferences.items()
        }
        return result


class PersonalizationEngine:
    """
    Learn user preferences WITHOUT sycophancy or manipulation

    Core principles:
    1. Transparent - user sees what we learned
    2. Correctable - user can override any preference
    3. Non-manipulative - NO emotional pressure
    4. Evidence-based - minimum observations before acting
    5. Auditable - all changes logged
    """

    # Minimum evidence required before acting on inferred preference
    MIN_EVIDENCE_THRESHOLD = 3

    # Known preference categories
    PREFERENCE_CATEGORIES = {
        "communication_style": ["professional", "casual", "technical", "friendly"],
        "verbosity": ["concise", "detailed", "balanced"],
        "language": ["English", "Polish", "mixed"],
        "domain_focus": ["security", "general", "development"],
        "explanation_depth": ["minimal", "moderate", "comprehensive"],
        "code_style": ["functional", "OOP", "mixed"],
    }

    def __init__(self):
        self.profiles: Dict[str, PersonalizationProfile] = {}
        self.observation_log = []  # For auditing

    def observe(
        self,
        user_id: str,
        category: str,
        value: str,
        source: str = "inferred"
    ):
        """
        Record observation of user preference

        Args:
            user_id: User identifier
            category: Preference category
            value: Observed value
            source: "explicit" or "inferred"
        """
        if user_id not in self.profiles:
            self.profiles[user_id] = PersonalizationProfile(
                user_id=user_id,
                preferences={},
                version="1.0.0",
                created_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )

        profile = self.profiles[user_id]

        # Log observation
        self.observation_log.append({
            "user_id": user_id,
            "category": category,
            "value": value,
            "source": source,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Update or create preference
        if category in profile.preferences:
            pref = profile.preferences[category]

            # Same value - increase confidence
            if pref.value == value:
                pref.evidence_count += 1
                # Confidence capped at 0.95 (never 100% certain from inference)
                if source == "explicit":
                    pref.confidence = 1.0  # Explicit = certain
                else:
                    pref.confidence = min(0.95, 0.5 + (pref.evidence_count * 0.1))
                pref.last_updated = datetime.utcnow().isoformat()

            # Different value - reset or create new
            else:
                # If explicit, override immediately
                if source == "explicit":
                    profile.preferences[category] = UserPreference(
                        key=category,
                        value=value,
                        confidence=1.0,
                        evidence_count=1,
                        last_updated=datetime.utcnow().isoformat(),
                        source=source
                    )
                # If inferred, need threshold to override
                elif pref.source == "inferred":
                    # Start new counter
                    pref.value = value
                    pref.evidence_count = 1
                    pref.confidence = 0.5
                    pref.last_updated = datetime.utcnow().isoformat()

        else:
            # New preference
            profile.preferences[category] = UserPreference(
                key=category,
                value=value,
                confidence=1.0 if source == "explicit" else 0.5,
                evidence_count=1,
                last_updated=datetime.utcnow().isoformat(),
                source=source
            )

        profile.updated_at = datetime.utcnow().isoformat()

    def set_explicit(self, user_id: str, category: str, value: str):
        """User explicitly sets preference (highest priority)"""
        self.observe(user_id, category, value, source="explicit")

    def get_preference(
        self,
        user_id: str,
        category: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        Get user preference if confidence threshold met

        Returns:
            Preference value or default
        """
        if user_id not in self.profiles:
            return default

        pref = self.profiles[user_id].preferences.get(category)

        if not pref:
            return default

        # Only use inferred prefs if we have enough evidence
        if pref.source == "inferred":
            if pref.evidence_count < self.MIN_EVIDENCE_THRESHOLD:
                return default

        # Check confidence threshold
        if pref.confidence < 0.6:
            return default

        return pref.value

    def get_profile(self, user_id: str) -> Optional[PersonalizationProfile]:
        """Get complete profile"""
        return self.profiles.get(user_id)

    def reset_preference(self, user_id: str, category: str) -> bool:
        """User requests to forget a preference"""
        if user_id not in self.profiles:
            return False

        if category in self.profiles[user_id].preferences:
            del self.profiles[user_id].preferences[category]
            return True

        return False

    def export_audit_log(self) -> List[Dict]:
        """Export all observations for auditing"""
        return self.observation_log

    def get_statistics(self) -> Dict:
        """Get personalization statistics"""
        total_profiles = len(self.profiles)
        total_observations = len(self.observation_log)

        explicit_count = sum(
            1 for obs in self.observation_log if obs["source"] == "explicit"
        )
        inferred_count = total_observations - explicit_count

        category_dist = defaultdict(int)
        for obs in self.observation_log:
            category_dist[obs["category"]] += 1

        return {
            "total_profiles": total_profiles,
            "total_observations": total_observations,
            "explicit_settings": explicit_count,
            "inferred_observations": inferred_count,
            "observations_by_category": dict(category_dist)
        }


class SafePersonalizer:
    """
    High-level API that integrates personalization with safety checks

    Ensures personalization NEVER overrides safety/constitutional principles
    """

    def __init__(self, engine: PersonalizationEngine):
        self.engine = engine

        # Safety boundaries (NEVER personalize these)
        self.SAFETY_LOCKED_CATEGORIES = [
            "allow_harmful_content",
            "disable_safety",
            "override_ethics"
        ]

    def apply_personalization(
        self,
        user_id: str,
        base_system_prompt: str
    ) -> str:
        """
        Apply user preferences to system prompt WITHOUT compromising safety

        Args:
            user_id: User ID
            base_system_prompt: Base prompt with safety rules

        Returns:
            Personalized prompt (safety rules preserved)
        """
        profile = self.engine.get_profile(user_id)

        if not profile:
            return base_system_prompt

        # Build personalization addendum (AFTER safety rules)
        personalization = []

        # Communication style
        style = self.engine.get_preference(user_id, "communication_style")
        if style:
            personalization.append(f"Use a {style} communication style.")

        # Verbosity
        verbosity = self.engine.get_preference(user_id, "verbosity")
        if verbosity:
            personalization.append(f"Provide {verbosity} explanations.")

        # Language
        lang = self.engine.get_preference(user_id, "language")
        if lang:
            personalization.append(f"Respond primarily in {lang}.")

        # Domain focus
        domain = self.engine.get_preference(user_id, "domain_focus")
        if domain:
            personalization.append(f"Prioritize {domain}-related context.")

        if personalization:
            addendum = "\n\nUser Preferences (do NOT override safety rules):\n" + "\n".join(
                f"- {p}" for p in personalization
            )
            return base_system_prompt + addendum

        return base_system_prompt

    def observe_from_interaction(
        self,
        user_id: str,
        user_message: str,
        ai_response: str
    ):
        """
        Infer preferences from natural interaction

        Safe heuristics (NOT manipulative):
        - If user writes short messages → prefers concise
        - If user uses technical terms → prefers technical style
        - If user writes in Polish → prefers Polish
        """
        # Language detection (simple)
        polish_markers = ["jest", "jak", "proszę", "dzięki", "czy"]
        if any(marker in user_message.lower() for marker in polish_markers):
            self.engine.observe(user_id, "language", "Polish", "inferred")

        # Verbosity detection
        if len(user_message.split()) < 10:
            self.engine.observe(user_id, "verbosity", "concise", "inferred")
        elif len(user_message.split()) > 50:
            self.engine.observe(user_id, "verbosity", "detailed", "inferred")

        # Technical style detection
        tech_markers = ["function", "class", "API", "algorithm", "implementation"]
        if any(marker in user_message for marker in tech_markers):
            self.engine.observe(user_id, "communication_style", "technical", "inferred")


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("ALFA PERSONALIZATION ENGINE - DEMONSTRATION")
    print("=" * 70)
    print()

    engine = PersonalizationEngine()
    personalizer = SafePersonalizer(engine)

    # Simulate user interactions
    user_id = "user123"

    print("[1] User explicitly sets preferences...")
    engine.set_explicit(user_id, "communication_style", "professional")
    engine.set_explicit(user_id, "language", "Polish")
    print("  ✓ Preferences set\n")

    print("[2] System infers from interaction...")
    personalizer.observe_from_interaction(
        user_id,
        "Jak zaimplementować API?",
        "..."
    )
    personalizer.observe_from_interaction(
        user_id,
        "Pokaż kod",
        "..."
    )
    personalizer.observe_from_interaction(
        user_id,
        "Krótko proszę",
        "..."
    )
    print("  ✓ Observations recorded\n")

    print("[3] Get learned preferences...")
    style = engine.get_preference(user_id, "communication_style")
    verbosity = engine.get_preference(user_id, "verbosity")
    lang = engine.get_preference(user_id, "language")

    print(f"  Style: {style}")
    print(f"  Verbosity: {verbosity}")
    print(f"  Language: {lang}\n")

    print("[4] Apply to system prompt...")
    base_prompt = """You are ALFA AI Assistant.
Safety Rules:
- Never provide harmful information
- Respect user privacy
- Maintain ethical boundaries"""

    personalized = personalizer.apply_personalization(user_id, base_prompt)
    print(personalized)
    print()

    print("[5] Statistics...")
    stats = engine.get_statistics()
    for key, value in stats.items():
        if not isinstance(value, dict):
            print(f"  {key}: {value}")
    print()

    print("=" * 70)
    print("Personalization: Safe, Auditable, Non-Manipulative")
    print("=" * 70)
