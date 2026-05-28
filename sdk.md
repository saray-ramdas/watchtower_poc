# SDK Guide (Aligned to `bilvantis_watchtower` API)

## 1) Technical Objective
Build a Python SDK where application teams only need to:
1. Initialize `Watchtower(...)` with policy packs and runtime settings.
2. Wrap any LLM client (`wt.wrap(client)`).
3. Use the wrapped client normally while security is enforced automatically.

## 2) Public API to Implement

```python
from bilvantis_watchtower import Watchtower
from bilvantis_watchtower.policies import UAEFinancialServicesPack, ShariaCompliancePack

wt = Watchtower(
    sft_model_path="/opt/watchtower/models/wt-pii-v2.4",
    policy_packs=[
        UAEFinancialServicesPack(version="2024.11"),
        ShariaCompliancePack(version="2024.10", board_rulings_path="/data/sharia"),
    ],
    audit_backend="postgres://audit-db/watchtower",
    perimeter_id="national-bonds-uae-north",
    fail_mode="closed",
)

safe_client = wt.wrap(raw_llm_client)
```

## 3) Implementation Steps (Concrete)
1. Package scaffold.
- Create `bilvantis_watchtower/` package and `pyproject.toml`.
- Export `Watchtower` and policy packs in `__init__.py`.

2. Define core types.
- `RequestContext`, `PolicyDecision`, `RiskAssessment`, `AuditEvent`, `SafeResponse`.
- Use Pydantic/dataclasses with explicit schema versioning.

3. Implement `Watchtower` class.
- Validate constructor args (`sft_model_path`, `policy_packs`, `fail_mode`).
- Build internal pipeline dependency graph.
- Initialize audit backend connector.

4. Implement policy-pack plugin system.
- `PolicyPack` abstract base class with `evaluate(...)`.
- Create `UAEFinancialServicesPack` and `ShariaCompliancePack`.
- Add deterministic decision aggregation (`DENY > ESCALATE > ALLOW`).

5. Implement `wrap(...)` proxy layer.
- Return a proxy object mirroring LLM client methods.
- Intercept prompt payload before outbound call.
- Apply pre-check pipeline and post-check pipeline automatically.

6. Build PII module.
- Presidio detectors for baseline entities.
- Custom recognizers for banking-domain identifiers.
- Optional local SFT detector using `sft_model_path` and confidence ensemble.
- Redaction format: deterministic placeholders.

7. Add guardrails and malicious intent routing.
- Detect prompt injection, policy override attempts, and exfil patterns.
- Route ambiguous high-risk requests to ReAct/escalation path.

8. Implement output post-check.
- Re-scan generated text for leaked sensitive entities.
- Redact or block according to policy and fail mode.

9. Audit and observability.
- Write structured events with `trace_id`, policy versions, pack IDs, risk score.
- Never store raw secrets/PII in logs.

10. Add robust error handling.
- `fail_mode="closed"`: deny response on critical pipeline failure.
- `fail_mode="warn"`: return response with warning metadata.
- `fail_mode="open"`: bypass controls only for approved low-risk contexts.

11. Test matrix.
- Unit: constructor validation, policy engine, detector behavior, wrapper proxy.
- Integration: wrapped Anthropic/OpenAI client flows.
- Security tests: cross-user data access denial, jailbreak attempts, obfuscated PII.

12. Versioning and release.
- Semantic versions.
- Pin policy pack versions in runtime metadata.
- Publish internal wheel and changelog.

## 4) Critical Vulnerabilities to Address
- Broken access control / IDOR.
  - Mitigate with server-side ownership checks in policy packs.
- Prompt injection and instruction override.
  - Mitigate with immutable guardrail layer before model invocation.
- PII leakage in outputs.
  - Mitigate with mandatory output post-check.
- Bypass by direct client use (no wrapper).
  - Mitigate via governance: block raw provider SDK usage in production services.
- Detector evasion (unicode/spacing obfuscation).
  - Mitigate with normalization + adversarial corpora + ensemble detection.

## 5) Recommended Defaults for Your Use Case
- `fail_mode="closed"`
- Minimum two policy packs: financial + Sharia/compliance.
- Post-check always on.
- Audit backend mandatory (Postgres or equivalent).
- Perimeter scoping required for every request.

## 6) Pros and Cons of This Exact SDK Pattern
Pros:
- Very low integration friction for app teams.
- Compliance updates shipped as policy pack versions.
- Uniform audit and guardrails across providers.

Cons:
- Wrapper maintenance overhead for provider SDK changes.
- Additional latency from multi-stage checks.
- False positives require operational tuning process.

## 7) Definition of Done
- Wrapped clients enforce both pre- and post-checks.
- Cross-user sensitive queries are denied consistently.
- PII is masked in requests and responses.
- Audit records include policy pack versions and trace IDs.
- SDK is packaged, tested, and documented with runnable examples.
