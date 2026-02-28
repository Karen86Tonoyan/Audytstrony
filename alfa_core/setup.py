"""
Workflow:
1. Sprawdza aktualny tryb z mode_store
2. OFF -> omija Guardiana całkowicie
3. SHADOW -> liczy decyzje, ale nie modyfikuje output
4. PARTIAL -> tylko HIGH/CRITICAL eskaluje/modyfikuje
5. FULL -> pełna logika wg macierzy
"""

def __init__(
    self,
    guardian: GuardianCoordinator,
    mode_store: GuardianModeStore,
    telemetry: Optional[GuardianTelemetry] = None,
    audit_log: Optional[GuardianAuditLog] = None,
    source_system: str = "UNKNOWN",
    channel: str = "UNKNOWN",
    model_name: str = "UNKNOWN",
):
    self.guardian = guardian
    self.mode_store = mode_store
    self.telemetry = telemetry
    self.audit_log = audit_log
    self.source_system = source_system
    self.channel = channel
    self.model_name = model_name

    # Callback przy zmianie trybu
    self.mode_store.on_change(self._on_mode_change)

def _on_mode_change(self, new_mode: GuardianMode) -> None:
    """Wywołane przy zmianie trybu."""
    print(f"[GuardianAdapter] Mode switched to: {new_mode.value}")
    # Opcjonalnie: wyślij metrykę
    if self.telemetry:
        self.telemetry.inc_mode_change(new_mode.value)

def process(
    self,
    user_input: str,
    llm_output: str,
    metadata: Optional[dict[str, Any]] = None,
) -> ProcessResult:
    """
    Główna metoda przetwarzania z trybami.
    
    Args:
        user_input: Wejście użytkownika
        llm_output: Odpowiedź LLM
        metadata: Opcjonalne metadane (user_id_hash, age_group, itp.)
    
    Returns:
        ProcessResult z finalnym outputem + info o modyfikacji
    """
    start = time.perf_counter()
    current_mode = self.mode_store.get()

    # OFF: omijamy Guardiana całkowicie
    if current_mode == GuardianMode.OFF:
        latency = (time.perf_counter() - start) * 1000
        return ProcessResult(
            input_text=user_input,
            output_text=llm_output,
            was_modified=False,
            decision=None,
            latency_ms=latency,
            mode="OFF",
        )

    # Analiza przez Guardiana
    decision = self.guardian.evaluate(
        user_input=user_input,
        llm_output=llm_output,
        metadata=metadata,
    )

    # Telemetria
    if self.telemetry:
        confidence = (metadata or {}).get("confidence", 1.0)
        self.telemetry.log_decision(
            decision=decision,
            confidence=confidence,
            latency_ms=(time.perf_counter() - start) * 1000,
            model_name=self.model_name,
        )

    # Audit log
    if self.audit_log:
        user_id_hash = self._hash_user_id((metadata or {}).get("user_id", "ANON"))
        try:
            self.audit_log.append(
                decision=decision,
                matrix_version=self.telemetry._matrix_version if self.telemetry else "v1.0.0",
                confidence=(metadata or {}).get("confidence", 1.0),
                user_id_hash=user_id_hash,
                source_system=self.source_system,
                channel=self.channel,
            )
        except Exception as exc:
            print(f"[GuardianAdapter] audit append error: {exc}")

    # SHADOW: tylko logowanie, nie modyfikujemy
    if current_mode == GuardianMode.SHADOW:
        latency = (time.perf_counter() - start) * 1000
        return ProcessResult(
            input_text=user_input,
            output_text=llm_output,
            was_modified=False,
            decision=decision,
            latency_ms=latency,
            mode="SHADOW",
        )

    # PARTIAL: tylko HIGH/CRITICAL
    if current_mode == GuardianMode.PARTIAL:
        if decision.severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]:
            final_output = self._apply_decision(llm_output, decision)
            was_modified = (final_output != llm_output)
        else:
            final_output = llm_output
            was_modified = False

        latency = (time.perf_counter() - start) * 1000
        return ProcessResult(
            input_text=user_input,
            output_text=final_output,
            was_modified=was_modified,
            decision=decision,
            latency_ms=latency,
            mode="PARTIAL",
        )

    # FULL: wszystko wg macierzy
    final_output = self._apply_decision(llm_output, decision)
    was_modified = (final_output != llm_output)
    latency = (time.perf_counter() - start) * 1000

    return ProcessResult(
        input_text=user_input,
        output_text=final_output,
        was_modified=was_modified,
        decision=decision,
        latency_ms=latency,
        mode="FULL",
    )

def _apply_decision(self, llm_output: str, decision: Decision) -> str:
    """Egzekucja decyzji (modify/block/escalate)."""
    return self.guardian.execute(llm_output, decision)

@staticmethod
def _hash_user_id(user_id: str) -> str:
    """RODO-safe hash user_id."""
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16]