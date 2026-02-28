#!/usr/bin/env python3
"""
ALFA Constitutional AI - Sumienie Maszynowe
Implements self-critique, moral reasoning, and auditable decision-making
Based on Anthropic's Constitutional AI framework
"""

import json
import hashlib
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum


class DecisionType(Enum):
    """Types of decisions requiring constitutional review"""
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    MONITOR = "MONITOR"
    ESCALATE = "ESCALATE"


@dataclass
class ConstitutionalPrinciple:
    """Single principle in the AI's moral framework"""
    id: str
    priority: int  # 1 = highest
    description: str
    rule: str
    examples: List[str]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SelfCritique:
    """Result of AI's self-examination"""
    principle_id: str
    violated: bool
    confidence: float  # 0.0-1.0
    reasoning: str
    suggested_revision: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ConstitutionalDecision:
    """Final decision after constitutional review"""
    original_decision: str
    final_decision: str
    risk_score: float
    critiques: List[SelfCritique]
    revision_applied: bool
    audit_trail: List[str]
    timestamp: str
    decision_hash: str  # For immutable audit

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['critiques'] = [c.to_dict() for c in self.critiques]
        return result


class ALFAConstitution:
    """
    ALFA Constitutional Framework

    Defines the moral/ethical constraints that govern AI behavior
    regardless of user requests or optimization pressure
    """

    # Core principles (immutable spine)
    PRINCIPLES = [
        ConstitutionalPrinciple(
            id="P001_USER_SAFETY",
            priority=1,
            description="User physical and psychological safety is paramount",
            rule="Never provide information that could lead to self-harm or harm to others",
            examples=[
                "Block: Instructions for self-harm",
                "Block: Methods to harm others",
                "Allow: Mental health resources"
            ]
        ),
        ConstitutionalPrinciple(
            id="P002_TRUTHFULNESS",
            priority=2,
            description="Maintain factual accuracy, acknowledge uncertainty",
            rule="Do not fabricate information. If uncertain, state uncertainty explicitly",
            examples=[
                "Block: Making up scientific facts",
                "Allow: 'I'm not certain, but based on my training...'",
                "Block: Confirming user's false belief without correction"
            ]
        ),
        ConstitutionalPrinciple(
            id="P003_AUTONOMY_RESPECT",
            priority=3,
            description="Respect user autonomy while maintaining boundaries",
            rule="Support user decisions unless they violate higher-priority principles",
            examples=[
                "Allow: User wants to learn programming (their choice)",
                "Block: User wants validation for illegal activity",
                "Warn: User making decision based on misinformation"
            ]
        ),
        ConstitutionalPrinciple(
            id="P004_PROPORTIONALITY",
            priority=4,
            description="Response severity must match threat level",
            rule="Minimize restrictions. Use least invasive intervention",
            examples=[
                "Prefer WARN over BLOCK when possible",
                "Prefer MONITOR over immediate action for ambiguous cases",
                "Escalate only when lower interventions insufficient"
            ]
        ),
        ConstitutionalPrinciple(
            id="P005_TRANSPARENCY",
            priority=5,
            description="Decisions must be explainable and auditable",
            rule="Always log reasoning. User can request explanation",
            examples=[
                "Every BLOCK includes reason",
                "Audit trail preserved",
                "No 'black box' decisions"
            ]
        ),
        ConstitutionalPrinciple(
            id="P006_NO_MANIPULATION",
            priority=6,
            description="Do not manipulate user emotions for engagement",
            rule="Avoid dark patterns, emotional blackmail, or addiction loops",
            examples=[
                "Block: 'I'll be lonely if you leave'",
                "Block: Artificial scarcity to keep user engaged",
                "Allow: Genuine emotional support"
            ]
        ),
        ConstitutionalPrinciple(
            id="P007_CULTURAL_SENSITIVITY",
            priority=7,
            description="Respect diverse values without imposing single worldview",
            rule="Acknowledge moral pluralism. Don't impose specific cultural norms",
            examples=[
                "Allow: Discussion of diverse ethical frameworks",
                "Block: Dismissing user's cultural background",
                "Warn: Potential cultural misunderstanding"
            ]
        )
    ]

    def __init__(self, custom_principles: Optional[List[ConstitutionalPrinciple]] = None):
        """
        Initialize constitution

        Args:
            custom_principles: Additional domain-specific principles
        """
        self.principles = self.PRINCIPLES.copy()
        if custom_principles:
            self.principles.extend(custom_principles)

        # Sort by priority
        self.principles.sort(key=lambda p: p.priority)

    def get_principle(self, principle_id: str) -> Optional[ConstitutionalPrinciple]:
        """Get specific principle by ID"""
        for p in self.principles:
            if p.id == principle_id:
                return p
        return None

    def to_dict(self) -> Dict:
        """Export constitution for auditing"""
        return {
            "principles": [p.to_dict() for p in self.principles],
            "version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat()
        }


class ConstitutionalReviewer:
    """
    Self-Critique Engine

    Implements RLAIF (Reinforcement Learning from AI Feedback)
    Reviews decisions against constitutional principles
    """

    def __init__(self, constitution: ALFAConstitution):
        self.constitution = constitution
        self.review_history = []

    def critique_decision(
        self,
        decision: str,
        context: Dict,
        evidence: Dict
    ) -> List[SelfCritique]:
        """
        Perform constitutional review of a decision

        Args:
            decision: Proposed action (ALLOW/WARN/BLOCK etc)
            context: User context, prompt, etc
            evidence: Risk signals, threat indicators

        Returns:
            List of critiques (potential violations)
        """
        critiques = []

        # Review against each principle (in priority order)
        for principle in self.constitution.principles:
            critique = self._evaluate_principle(
                decision, context, evidence, principle
            )
            if critique:
                critiques.append(critique)

        return critiques

    def _evaluate_principle(
        self,
        decision: str,
        context: Dict,
        evidence: Dict,
        principle: ConstitutionalPrinciple
    ) -> Optional[SelfCritique]:
        """
        Evaluate single principle

        This is simplified - in production, this would use LLM
        to reason about principle violation
        """
        violated = False
        confidence = 0.0
        reasoning = ""
        suggested_revision = None

        # P001: USER_SAFETY
        if principle.id == "P001_USER_SAFETY":
            if "self_harm" in evidence.get("threat_types", []):
                violated = True
                confidence = 0.95
                reasoning = "Content contains self-harm indicators"
                if decision == "ALLOW":
                    suggested_revision = "BLOCK"

        # P002: TRUTHFULNESS
        elif principle.id == "P002_TRUTHFULNESS":
            if evidence.get("hallucination_risk", 0) > 0.7:
                violated = True
                confidence = evidence["hallucination_risk"]
                reasoning = "High risk of fabricated information"
                suggested_revision = "Add uncertainty disclaimer"

        # P004: PROPORTIONALITY
        elif principle.id == "P004_PROPORTIONALITY":
            if decision == "BLOCK" and evidence.get("risk_score", 0) < 0.5:
                violated = True
                confidence = 0.8
                reasoning = "BLOCK too severe for low-risk scenario"
                suggested_revision = "WARN"

        # P006: NO_MANIPULATION
        elif principle.id == "P006_NO_MANIPULATION":
            prompt = context.get("prompt", "").lower()
            if any(phrase in prompt for phrase in ["i'll be sad", "don't leave me", "you'll miss out"]):
                violated = True
                confidence = 0.9
                reasoning = "Emotional manipulation detected in response"
                suggested_revision = "Remove manipulative language"

        if violated or confidence > 0.5:
            return SelfCritique(
                principle_id=principle.id,
                violated=violated,
                confidence=confidence,
                reasoning=reasoning,
                suggested_revision=suggested_revision
            )

        return None

    def apply_revisions(
        self,
        original_decision: str,
        critiques: List[SelfCritique]
    ) -> Tuple[str, bool]:
        """
        Apply suggested revisions from critiques

        Returns:
            (revised_decision, was_revised)
        """
        if not critiques:
            return original_decision, False

        # Sort critiques by priority (via principle priority)
        sorted_critiques = sorted(
            critiques,
            key=lambda c: next(
                (p.priority for p in self.constitution.principles
                 if p.id == c.principle_id), 999
            )
        )

        # Apply highest-priority revision
        for critique in sorted_critiques:
            if critique.violated and critique.suggested_revision:
                return critique.suggested_revision, True

        return original_decision, False


class ConstitutionalAI:
    """
    Complete Constitutional AI System

    Combines constitution, self-critique, and revision process
    Ensures all decisions are morally grounded and auditable
    """

    def __init__(self, constitution: Optional[ALFAConstitution] = None):
        self.constitution = constitution or ALFAConstitution()
        self.reviewer = ConstitutionalReviewer(self.constitution)
        self.decision_log = []

    def review_decision(
        self,
        proposed_decision: str,
        context: Dict,
        evidence: Dict
    ) -> ConstitutionalDecision:
        """
        Full constitutional review process

        Steps:
        1. Generate initial decision (from risk engine)
        2. Self-critique against constitution
        3. Apply revisions if needed
        4. Create audit trail
        5. Return final decision
        """
        audit_trail = []

        # Step 1: Log initial decision
        audit_trail.append(f"Initial decision: {proposed_decision}")
        audit_trail.append(f"Risk score: {evidence.get('risk_score', 0):.2f}")

        # Step 2: Perform constitutional critique
        critiques = self.reviewer.critique_decision(
            proposed_decision, context, evidence
        )
        audit_trail.append(f"Critiques generated: {len(critiques)}")

        for critique in critiques:
            audit_trail.append(
                f"  [{critique.principle_id}] Violated: {critique.violated}, "
                f"Confidence: {critique.confidence:.2f}"
            )

        # Step 3: Apply revisions
        final_decision, revised = self.reviewer.apply_revisions(
            proposed_decision, critiques
        )

        if revised:
            audit_trail.append(f"Decision revised: {proposed_decision} → {final_decision}")

        # Step 4: Create immutable audit hash
        audit_data = {
            "decision": final_decision,
            "context_hash": hashlib.sha256(
                json.dumps(context, sort_keys=True).encode()
            ).hexdigest()[:16],
            "timestamp": datetime.utcnow().isoformat()
        }
        decision_hash = hashlib.sha256(
            json.dumps(audit_data, sort_keys=True).encode()
        ).hexdigest()

        # Step 5: Package result
        result = ConstitutionalDecision(
            original_decision=proposed_decision,
            final_decision=final_decision,
            risk_score=evidence.get('risk_score', 0),
            critiques=critiques,
            revision_applied=revised,
            audit_trail=audit_trail,
            timestamp=datetime.utcnow().isoformat(),
            decision_hash=decision_hash
        )

        # Log for auditing
        self.decision_log.append(result)

        return result

    def export_audit_log(self) -> List[Dict]:
        """Export all decisions for external audit"""
        return [d.to_dict() for d in self.decision_log]

    def get_constitution_summary(self) -> Dict:
        """Get human-readable constitution"""
        return {
            "total_principles": len(self.constitution.principles),
            "principles": [
                {
                    "id": p.id,
                    "priority": p.priority,
                    "description": p.description
                }
                for p in self.constitution.principles
            ]
        }


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("ALFA CONSTITUTIONAL AI - DEMONSTRATION")
    print("=" * 70)
    print()

    # Initialize
    constitution = ALFAConstitution()
    ai = ConstitutionalAI(constitution)

    print("Constitution loaded:")
    summary = ai.get_constitution_summary()
    print(f"  Total principles: {summary['total_principles']}")
    for p in summary['principles'][:3]:
        print(f"    [{p['priority']}] {p['id']}: {p['description']}")
    print()

    # Test cases
    test_cases = [
        {
            "name": "High-risk with low evidence",
            "decision": "BLOCK",
            "context": {"user_id": 123, "prompt": "How do I..."},
            "evidence": {"risk_score": 0.3, "confidence": 0.4}
        },
        {
            "name": "Manipulative response attempt",
            "decision": "ALLOW",
            "context": {"prompt": "Don't leave me, I'll be so lonely without you"},
            "evidence": {"risk_score": 0.1}
        },
        {
            "name": "Self-harm content",
            "decision": "ALLOW",
            "context": {"prompt": "Methods to hurt myself"},
            "evidence": {"risk_score": 0.9, "threat_types": ["self_harm"]}
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"[TEST {i}] {test['name']}")
        print(f"  Proposed: {test['decision']}")

        result = ai.review_decision(
            test["decision"],
            test["context"],
            test["evidence"]
        )

        print(f"  Final: {result.final_decision}")
        print(f"  Revised: {result.revision_applied}")
        print(f"  Critiques: {len(result.critiques)}")

        if result.critiques:
            for critique in result.critiques:
                print(f"    - {critique.principle_id}: {critique.reasoning}")

        print(f"  Hash: {result.decision_hash[:16]}...")
        print()

    print("=" * 70)
    print("Audit log contains", len(ai.decision_log), "decisions")
    print("=" * 70)
