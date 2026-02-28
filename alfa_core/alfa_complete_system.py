#!/usr/bin/env python3
"""
ALFA COMPLETE SYSTEM
Constitutional AI + Optimized Memory + Safe Personalization + OpenAI Integration

Cold-tech, auditable, non-manipulative companion system
"""

import os
import asyncio
from typing import Dict, Optional, Any

# Import ALFA components
from alfa_constitutional_ai import (
    ALFAConstitution,
    ConstitutionalAI,
    DecisionType
)
from alfa_optimized_memory import (
    OptimizedMemoryStore,
    UserProfileMemory,
    MemoryPriority
)
from alfa_personalization import (
    PersonalizationEngine,
    SafePersonalizer
)
from openai_integration import ALFAIntelligence
from alfa_openai_core import ALFACoreIntelligence


class ALFACompleteSystem:
    """
    ALFA Complete Companion System
    
    Layers:
    1. Constitutional AI (sumienie - moral framework)
    2. Optimized Memory (pamięć - weighted, bounded)
    3. Personalization (preferencje - without manipulation)
    4. OpenAI Integration (execution engine)
    """
    
    def __init__(self, openai_api_key: Optional[str] = None):
        # Layer 1: Constitutional AI
        self.constitutional_ai = ConstitutionalAI()
        
        # Layer 2: Memory
        self.memory_store = OptimizedMemoryStore()
        self.user_memory = UserProfileMemory(self.memory_store)
        
        # Layer 3: Personalization
        self.personalization = PersonalizationEngine()
        self.personalizer = SafePersonalizer(self.personalization)
        
        # Layer 4: OpenAI
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if self.openai_key:
            self.ai_core = ALFACoreIntelligence(api_key=self.openai_key)
        else:
            print("⚠️ OpenAI API key not found - running in offline mode")
            self.ai_core = None
    
    async def process_message(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Complete message processing pipeline
        
        Steps:
        1. Load user profile (memory + preferences)
        2. Apply constitutional review
        3. If safe → personalize system prompt
        4. Call OpenAI
        5. Update memory with interaction
        6. Return result + audit trail
        """
        context = context or {}
        context["user_id"] = user_id
        
        # Step 1: Load profile
        user_profile = self.user_memory.get_profile(user_id)
        personalization_profile = self.personalization.get_profile(user_id)
        
        # Step 2: Constitutional review (safety check)
        initial_decision = "ALLOW"  # Default
        evidence = {"risk_score": 0.0}  # Would come from risk engine
        
        const_review = self.constitutional_ai.review_decision(
            initial_decision,
            {"user_id": user_id, "prompt": message},
            evidence
        )
        
        if const_review.final_decision == "BLOCK":
            return {
                "blocked": True,
                "reason": "Constitutional violation",
                "audit": const_review.to_dict()
            }
        
        # Step 3: Personalize system prompt
        base_prompt = """You are ALFA AI Assistant.
Safety Rules:
- Maintain ethical boundaries
- No emotional manipulation
- Transparent and auditable"""
        
        personalized_prompt = self.personalizer.apply_personalization(
            user_id,
            base_prompt
        )
        
        # Step 4: Call OpenAI (if available)
        if self.ai_core:
            result = await self.ai_core.safe_completion(
                message,
                model="gpt-3.5-turbo"
            )
        else:
            result = {
                "blocked": False,
                "completion": "[Offline mode - no OpenAI]",
                "assessment": {}
            }
        
        # Step 5: Update memory
        # Store important context only
        if not result.get("blocked"):
            self.personalizer.observe_from_interaction(
                user_id,
                message,
                result.get("completion", "")
            )
        
        # Step 6: Package response
        return {
            **result,
            "constitutional_review": const_review.to_dict(),
            "user_profile": user_profile,
            "personalization": personalization_profile.to_dict() if personalization_profile else None
        }
    
    def get_system_status(self) -> Dict:
        """Get complete system status"""
        return {
            "constitutional_ai": {
                "principles": len(self.constitutional_ai.constitution.principles),
                "decisions_made": len(self.constitutional_ai.decision_log)
            },
            "memory": self.memory_store.get_statistics(),
            "personalization": self.personalization.get_statistics(),
            "openai_available": self.ai_core is not None
        }


async def main():
    """Demo of complete system"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║         ALFA COMPLETE SYSTEM v3.0                         ║
║                                                           ║
║  Constitutional AI + Memory + Personalization + OpenAI   ║
║          Cold-Tech, Auditable, Non-Manipulative          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    system = ALFACompleteSystem()
    
    print("System Status:")
    status = system.get_system_status()
    print(f"  Constitutional Principles: {status['constitutional_ai']['principles']}")
    print(f"  Memory Entries: {status['memory']['current_entries']}")
    print(f"  Personalization Profiles: {status['personalization']['total_profiles']}")
    print(f"  OpenAI Available: {status['openai_available']}")
    print()
    
    # Simulate interaction
    user_id = "demo_user"
    
    print("[Demo] User sets preferences...")
    system.personalization.set_explicit(user_id, "communication_style", "technical")
    system.personalization.set_explicit(user_id, "language", "Polish")
    system.user_memory.remember_boundary(user_id, "Never discuss politics")
    print("  ✓ Preferences stored\n")
    
    print("[Demo] Processing message...")
    result = await system.process_message(
        user_id,
        "Wyjaśnij jak działa ALFA system"
    )
    
    print(f"  Blocked: {result['blocked']}")
    if not result['blocked']:
        print(f"  Response length: {len(result.get('completion', ''))} chars")
        print(f"  Constitutional review: {result['constitutional_review']['final_decision']}")
    print()
    
    print("=" * 70)
    print("System operational and auditable")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
