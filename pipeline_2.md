# Pipeline 2: Parallel Backend Delivery Plan

## Goal
Build the lottery eligibility backend with clear file ownership so Satwik and Anshul can work at the same time without editing the same files.

## Current MVP Scope
Included:
- FastAPI backend
- SQLAlchemy MySQL integration
- Master agent orchestration
- Savings Agent, Prize Money Agent, and Response Agent
- Lottery eligibility flow

Not included for now:
- Tokenization
- Reverse tokenization
- Security-layer harmful query detection
- UI implementation

## Business Rule
A user is eligible for the lottery only when both conditions are true:
- `balance > 50000`
- `years_in_bank >= 3`

## Database Model
Use one table for the MVP:

```sql
customer_lottery_profile
```

Columns:
- `user_id` (PK)
- `full_name`
- `balance`
- `years_in_bank`
- `updated_at`

## Shared Runtime State
The agent flow should pass this state object:

- `user_id`
- `original_query`
- `normalized_intent`
- `balance`
- `years_in_bank`
- `eligible`
- `decision_reason`
- `final_response`

## Phase 0: Foundation Already Prepared
Owner: Satwik

Purpose:
- Keep the backend runnable before agent work starts.

Files owned by Satwik:
- `orchestrator_app/app/main.py`
- `orchestrator_app/app/db/base.py`
- `orchestrator_app/app/db/session.py`
- `orchestrator_app/app/db/models.py`
- `orchestrator_app/app/db/__init__.py`
- `requirements.txt`
- `.env`
- `configs/env/.env.example`

Do not edit these files:
- Anshul should not edit these unless Satwik asks him to.

Done when:
- FastAPI starts.
- MySQL table auto-creates through lifespan.
- `/health` returns `{"status":"ok"}`.

## Phase 1: Shared Contracts
Owner: Satwik first, then freeze

Purpose:
- Define the shared shape both developers will rely on.

Files owned by Satwik:
- `orchestrator_app/app/graph/state.py`
- `orchestrator_app/app/api/schemas.py`

Tasks:
- Define the runtime state fields listed above.
- Define request and response schemas.
- Keep contracts small and stable.

Done when:
- Anshul can import/use the state shape without needing to edit it.
- After this phase, both files are frozen unless both developers agree.

## Phase 2: Savings Agent + DB Tool
Owner: Anshul

Purpose:
- Fetch customer balance and years in bank from MySQL.

Files owned by Anshul:
- `orchestrator_app/app/agents/savings_agent.py`
- `orchestrator_app/app/tools/banking_tools.py`

Tasks:
- Implement a DB helper that reads from `customer_lottery_profile`.
- Implement Savings Agent that returns:
  - `balance`
  - `years_in_bank`
- Handle missing user cleanly.

Suggested SQL:

```sql
SELECT user_id, full_name, balance, years_in_bank, updated_at
FROM customer_lottery_profile
WHERE user_id = :user_id;
```

Do not edit:
- `orchestrator_app/app/agents/master_agent.py`
- `orchestrator_app/app/graph/workflow.py`
- `orchestrator_app/app/api/routes.py`
- `orchestrator_app/app/graph/state.py`
- `orchestrator_app/app/api/schemas.py`

Done when:
- Savings Agent can return facts for a valid `user_id`.
- Missing user returns a predictable error/result.

## Phase 3: Prize Money Agent
Owner: Anshul

Purpose:
- Decide lottery eligibility from balance and years in bank.

Files owned by Anshul:
- `orchestrator_app/app/agents/prize_money_agent.py`

Tasks:
- Accept `balance` and `years_in_bank`.
- Apply the exact rule:
  - `eligible = balance > 50000 and years_in_bank >= 3`
- Return:
  - `eligible`
  - `decision_reason`

Do not edit:
- Satwik-owned orchestration, API, and graph files.

Done when:
- `balance = 50000` returns not eligible.
- `years_in_bank = 3` passes the tenure rule.

## Phase 4: Response Agent
Owner: Anshul

Purpose:
- Convert the decision into final user-facing text.

Files owned by Anshul:
- `orchestrator_app/app/agents/response_agent.py`

Tasks:
- Generate final response from:
  - `eligible`
  - `decision_reason`
  - `balance`
  - `years_in_bank`
- Keep the response clear and short.

Do not edit:
- Satwik-owned orchestration, API, and graph files.

Done when:
- Eligible and non-eligible users both receive understandable responses.

## Phase 5: Master Agent
Owner: Satwik

Purpose:
- Control the end-to-end agent sequence.

Files owned by Satwik:
- `orchestrator_app/app/agents/master_agent.py`

Tasks:
- Receive `user_id` and `original_query`.
- Build initial state.
- Call Savings Agent.
- Call Prize Money Agent.
- Call Response Agent.
- Return final state.

Do not edit:
- `orchestrator_app/app/agents/savings_agent.py`
- `orchestrator_app/app/tools/banking_tools.py`
- `orchestrator_app/app/agents/prize_money_agent.py`
- `orchestrator_app/app/agents/response_agent.py`

Done when:
- One Master Agent call returns `final_response`.

## Phase 6: Workflow Wiring
Owner: Satwik

Purpose:
- Wire the flow into the graph layer.

Files owned by Satwik:
- `orchestrator_app/app/graph/workflow.py`

Tasks:
- Add graph nodes for the agent flow.
- Keep edges deterministic:
  - Master start
  - Savings
  - Prize Money
  - Response
  - End

Do not edit:
- Anshul-owned agent implementation files.

Done when:
- Graph execution gives the same result as direct Master Agent execution.

## Phase 7: API Integration
Owner: Satwik

Purpose:
- Expose the final flow through FastAPI.

Files owned by Satwik:
- `orchestrator_app/app/api/routes.py`

Tasks:
- Accept `user_id` and `query`.
- Call Master Agent or workflow.
- Return final API response.

Do not edit:
- Anshul-owned agent implementation files.

Done when:
- `POST /api/v1/eligibility` returns the final response from the Response Agent.

## Phase 8: Tests
Owner: Split by file ownership

Anshul tests:
- Savings Agent tests
- Prize Money Agent tests
- Response Agent tests

Satwik tests:
- Master Agent tests
- Workflow tests
- API integration tests

Rule:
- Each person only tests their owned files unless both agree to pair on integration.

Done when:
- Happy path eligible user passes.
- Happy path non-eligible user passes.
- Boundary case `balance = 50000` passes.
- Boundary case `years_in_bank = 3` passes.

## File Ownership Summary
Satwik owns:
- `orchestrator_app/app/main.py`
- `orchestrator_app/app/api/routes.py`
- `orchestrator_app/app/api/schemas.py`
- `orchestrator_app/app/graph/state.py`
- `orchestrator_app/app/graph/workflow.py`
- `orchestrator_app/app/agents/master_agent.py`
- `orchestrator_app/app/db/base.py`
- `orchestrator_app/app/db/session.py`
- `orchestrator_app/app/db/models.py`
- `requirements.txt`
- `.env`
- `configs/env/.env.example`

Anshul owns:
- `orchestrator_app/app/agents/savings_agent.py`
- `orchestrator_app/app/tools/banking_tools.py`
- `orchestrator_app/app/agents/prize_money_agent.py`
- `orchestrator_app/app/agents/response_agent.py`

Shared only after discussion:
- `pipeline_2.md`
- `README.md`
- `problem_statement.md`
- `arch.md`

## Conflict Avoidance Rules
1. Do not edit files owned by the other person.
2. Finish and freeze Phase 1 before parallel work starts.
3. If a contract change is needed, pause and update `state.py` or `schemas.py` first.
4. Pull latest before starting work each day.
5. Commit only your owned files.
6. Merge order should be:
   - Phase 1 shared contracts
   - Anshul agent files
   - Satwik master/workflow/API files

## Recommended Branch Flow
Satwik:
```bash
git checkout satwik
git pull origin satwik
```

Anshul:
```bash
git fetch origin
git checkout anshul
git pull origin satwik
```

After pulling Satwik's base, Anshul should commit only Anshul-owned files.

## Acceptance Checklist
- FastAPI starts without crashing.
- MySQL table exists.
- Savings Agent fetches `balance` and `years_in_bank`.
- Prize Money Agent applies the eligibility rule exactly.
- Response Agent creates a final reasoned answer.
- Master Agent calls the sub-agents in order.
- API returns only the final eligibility response.
- Satwik and Anshul do not edit the same implementation files.
