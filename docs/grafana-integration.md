# Integracja z Grafaną — SHARON jako dashboard SOC

Wyniki skanów z [playbooka obrony](anti-surveillance-playbook.md) i metryki z bramy
SOMEN6 trafiają do Grafany, tworząc panel SHARON — jeden widok stanu bezpieczeństwa
Twojej floty urządzeń.

> **Zakres.** Panel monitoruje urządzenia należące do Ciebie / Twojej organizacji.
> To standardowy monitoring własnej floty (jak każdy SOC), nie obserwacja osób trzecich.

---

## Architektura przepływu danych

```
┌──────────────────┐   metryki (Prometheus text)   ┌──────────────┐
│  Skanery / sweep │──────────────────────────────▶│  Prometheus  │
│  (MVT, Defender, │                                └──────┬───────┘
│   Malwarebytes,  │   logi / timeline (JSON)              │
│   SOMEN6 Bridge) │──────────────────────────┐           │
└──────────────────┘                          ▼           ▼
                                        ┌──────────┐  ┌──────────┐
                                        │   Loki   │  │ Grafana  │
                                        │  (logi)  │◀─│ (SHARON) │
                                        └──────────┘  └──────────┘
```

- **Prometheus** — metryki liczbowe (ile urządzeń, ile zagrożeń, kiedy ostatni skan)
- **Loki** — logi i osie czasu skanów (szczegóły wykryć, artefakty)
- **Grafana** — panel SHARON: alerty, trendy, stan zgodności

SOMEN6 Bridge już wystawia `/metrics` w natywnym formacie Prometheus — wpina się
bez zmian.

---

## Schemat metryk SHARON

Konwencja nazw zgodna z Prometheus (`snake_case`, sufiks `_total` dla liczników).
Każda metryka etykietowana `device_id` i `platform`.

```
# HELP sharon_device_scans_total Liczba wykonanych skanów urządzenia
# TYPE sharon_device_scans_total counter
sharon_device_scans_total{device_id="phone-01",platform="android"} 42

# HELP sharon_threats_detected_total Wykryte zagrożenia wg wagi
# TYPE sharon_threats_detected_total counter
sharon_threats_detected_total{device_id="phone-01",platform="android",severity="high"} 0
sharon_threats_detected_total{device_id="phone-01",platform="android",severity="medium"} 2

# HELP sharon_last_scan_timestamp_seconds Czas ostatniego skanu (unix)
# TYPE sharon_last_scan_timestamp_seconds gauge
sharon_last_scan_timestamp_seconds{device_id="phone-01",platform="android"} 1756000000

# HELP sharon_device_compliant Czy urządzenie spełnia politykę (1/0)
# TYPE sharon_device_compliant gauge
sharon_device_compliant{device_id="phone-01",platform="android"} 1

# HELP sharon_suspicious_permissions Liczba aplikacji z groźnymi uprawnieniami
# TYPE sharon_suspicious_permissions gauge
sharon_suspicious_permissions{device_id="phone-01",platform="android"} 3
```

Mapowanie źródeł na metryki:

| Źródło | Metryka |
|---|---|
| MVT (telefon) | `sharon_threats_detected_total{severity=...}` |
| Play Protect / Malwarebytes | `sharon_threats_detected_total`, `sharon_suspicious_permissions` |
| Defender Offline (Windows) | `sharon_threats_detected_total`, `sharon_device_compliant` |
| Każdy sweep | `sharon_device_scans_total`, `sharon_last_scan_timestamp_seconds` |
| SOMEN6 Bridge | `somen6_*` (już istnieją) |

---

## Przykładowe panele (PromQL)

**Urządzenia bez skanu > 24h** (stat / tabela):
```promql
(time() - sharon_last_scan_timestamp_seconds) > 86400
```

**Zagrożenia wysokiej wagi w całej flocie** (stat, próg alertu > 0):
```promql
sum(sharon_threats_detected_total{severity="high"})
```

**Odsetek urządzeń zgodnych z polityką** (gauge):
```promql
avg(sharon_device_compliant) * 100
```

**Urządzenia z groźnymi uprawnieniami** (bar gauge, sort malejąco):
```promql
topk(10, sharon_suspicious_permissions)
```

---

## Logi i osie czasu (Loki)

Szczegóły wykryć i timeline forensyczny idą do Loki jako JSON, strumień etykietowany
`{job="sharon", device_id="...", scan_type="..."}`:

```json
{"ts":"2026-08-24T10:00:00Z","device_id":"phone-01","scan_type":"mvt","level":"warn","finding":"suspicious_process","detail":"..."}
```

W Grafanie: panel Logs z filtrem po `device_id`, korelowany z metrykami na wspólnej osi czasu.

---

## Provisioning (dashboard jako kod)

Datasource i dashboardy trzymamy w repo jako YAML/JSON — powtarzalne, wersjonowane.

```yaml
# provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: ${PROMETHEUS_URL}      # z env, nie na sztywno
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: ${LOKI_URL}
```

> **Bezpieczeństwo.** Adresy, tokeny i klucze wyłącznie przez zmienne środowiskowe
> (`${VAR}`) — nigdy w plikach commitowanych do repo. Dostęp do Grafany za
> uwierzytelnianiem, docelowo **WebAuthn/FIDO2** (patrz warstwa Cerber w architekturze).

---

## Alerty

Grafana Alerting (lub Alertmanager) na regułach:

- zagrożenie `severity=high` gdziekolwiek → alert natychmiastowy,
- urządzenie bez skanu > 24h → alert ostrzegawczy,
- spadek `sharon_device_compliant` poniżej progu → alert.

Kanały: powiadomienie w panelu + opcjonalnie tryb alarmowy ALFA Phone.

---

## Powiązania

- [Playbook obrony](anti-surveillance-playbook.md) — źródło skanów zasilających metryki
- [Architektura ALFA Phone](alfa-phone-architecture.md) — Cerber jako warstwa auth panelu
- [Karta forensyki](forensics-android.md) — procedura, gdy panel pokaże wykrycie
