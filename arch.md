# Unified Architecture: Watch Tower SDK + Project

## 1) Purpose
This architecture is the single source of truth for both:
- `bilvantis_watchtower` SDK (security wrapper package)
- End-to-end Watch Tower project (agents, orchestration, API/UI, tests, ops)

Use this file to assign workstreams so teammates can build in parallel.

## 2) Architecture Layers
1. Client Layer
- Web/UI/API clients that submit user prompts.

2. Watch Tower SDK Layer (`bilvantis_watchtower`)
- Pre-LLM security checks, policy enforcement, PII masking.
- Post-LLM response safety checks and auditing.
- Exposes `Watchtower(...)` and `wt.wrap(llm_client)`.

3. Orchestrator + Agent Layer (`orchestrator_app`)
- Master/Orchestrator agent coordinates Savings, Prize, Response, ReAct agents.
- Business workflow and tool orchestration (LangGraph).

4. Platform Layer
- Datastores, audit backend, policy registry, observability, CI/CD.

## 3) Runtime Flow
1. App receives user request.
2. Request goes through wrapped model client (`safe_client = wt.wrap(raw_client)`).
3. SDK pre-checks:
- identity/context validation
- policy packs evaluation
- guardrails (jailbreak/injection/exfiltration)
- PII masking (Presidio + local SFT/Qwen-assisted detector)
4. Sanitized prompt goes to Master Agent.
5. Master Agent routes to domain agents and tools.
6. Model output returns through SDK post-check:
- output PII/policy leak scan
- redact/block according to policy
7. SDK writes audit event and returns safe response.

## 4) Unified Repository Structure
```text
watchtower_poc/
  README.md
  problem_statement.md
  arch.md
  sdk.md

  bilvantis_watchtower/                    # SDK package (reusable)
    pyproject.toml
    README.md
    src/bilvantis_watchtower/
      __init__.py                          # exports Watchtower
      watchtower.py                        # Watchtower constructor + wrap()
      wrapper.py                           # wrapped LLM proxy
      types.py                             # typed contracts
      exceptions.py
      config/
        defaults.py
        schema.py
      policies/
        __init__.py
        base.py                            # PolicyPack interface
        engine.py                          # decision aggregation
        uae_financial_services.py
        sharia_compliance.py
      security/
        guardrails.py
        malicious_intent.py
        enforcement.py
      pii/
        presidio_detector.py
        sft_detector.py
        ensemble.py
        redactor.py
        entity_catalog.py
      output/
        postcheck.py
        response_filters.py
      audit/
        backend.py
        postgres_backend.py
        signer.py
      observability/
        logging.py
        metrics.py
        tracing.py

    tests/
      unit/
      integration/
      adversarial/

  orchestrator_app/                        # Project/business logic app
    pyproject.toml
    README.md
    app/
      main.py                              # app entrypoint
      api/
        routes.py                          # request handlers
        schemas.py
      graph/
        workflow.py                        # LangGraph wiring
        state.py
      agents/
        master_agent.py                    # Orchestrator (Super Admin)
        savings_agent.py                   # get balance, years_in_bank
        prize_money_agent.py               # eligibility checks
        response_agent.py                  # yes/no response construction
        react_agent.py                     # malicious intent handling
      tools/
        banking_tools.py
        eligibility_tools.py
      services/
        user_context_service.py
        policy_context_service.py
      prompts/
        master_prompt.txt
        savings_prompt.txt
        prize_prompt.txt
        response_prompt.txt
        react_prompt.txt
      clients/
        llm_client.py                      # raw provider clients
        watchtower_adapter.py              # safe_client creation

    tests/
      unit/
      integration/
      e2e/

  infra/                                   # deployment + platform config
    docker/
      Dockerfile.sdk
      Dockerfile.app
    compose/
      docker-compose.yml
    k8s/
      sdk-deployment.yaml
      app-deployment.yaml
      postgres-audit.yaml
    terraform/
      modules/

  configs/
    env/
      .env.example
    policies/
      uae_finance_policy.yaml
      sharia_policy.yaml
    recognizers/
      custom_entities.yaml

  scripts/
    setup_dev.ps1
    run_tests.ps1
    seed_policy_store.ps1
    benchmark_pii.ps1

  docs/
    api-contracts.md
    threat-model.md
    guardrails-spec.md
    policy-pack-dev-guide.md
    runbooks/
      incident-response.md
      pii-false-positive-handling.md
      policy-rollout.md
```

## 5) Team Ownership (Parallel Work)
- Engineer A: `bilvantis_watchtower/policies/*`, `security/*`
- Engineer B: `bilvantis_watchtower/pii/*`, `output/*`
- Engineer C: `orchestrator_app/agents/*`, `graph/*`
- Engineer D: `orchestrator_app/api/*`, `services/*`, integration tests
- Engineer E: `infra/*`, observability, CI/CD

## 6) Boundaries: What Goes Where
SDK (`bilvantis_watchtower`) should contain:
- Generic security enforcement logic reusable across applications.
- Policy pack plugin contracts and implementations.
- Wrapper-level auditing and fail-mode behavior.

Orchestrator app (`orchestrator_app`) should contain:
- All domain/business agents.
- LangGraph orchestration and tool usage.
- Product-specific prompts and workflows.

Rule: no business workflow logic inside SDK.

## 7) Security Requirements (Non-Negotiable)
- Default `fail_mode="closed"` for production.
- Output post-check cannot be disabled in prod.
- No raw PII in logs/traces/errors/audit payloads.
- Policy versions and active pack list attached to each trace.
- Strict `perimeter_id` scoping for tenant isolation.

## 8) Vulnerabilities and Controls
- Broken access control
  - Control: policy packs enforce subject-resource ownership.
- Prompt injection/jailbreak
  - Control: guardrail stage before LLM invocation.
- Data exfiltration via agents/tools
  - Control: tool-level allowlists and scoped credentials.
- PII leakage in output
  - Control: mandatory post-check + redaction/block.
- SDK bypass by direct provider calls
  - Control: code governance and CI checks disallow raw LLM client usage.

## 9) Delivery Plan
1. Create repo skeleton and package scaffolds.
2. Implement SDK core (`Watchtower`, `wrap`, policy engine, fail modes).
3. Implement agents and LangGraph workflow.
4. Integrate app with wrapped safe client.
5. Add adversarial tests and audit validation.
6. Deploy with observability dashboards and rollout controls.

## 10) Definition of Done
- Teammates can work independently in assigned folders with minimal merge conflicts.
- Wrapped client is used in orchestrator path (no raw model calls in prod path).
- Cross-user sensitive access is blocked.
- PII is masked in input and output paths.
- Audit trail is complete and queryable by `trace_id`.
