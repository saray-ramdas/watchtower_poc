# Pipeline 2: Master Agent + Sub-Agents Delivery Plan

## Scope for This Pipeline
This plan covers only:
- Master agent orchestration
- Savings, Prize Money, and Response sub-agents
- End-to-end eligibility decision flow
- Single-table MVP data model: `customer_lottery_profile`

Out of scope for now:
- Tokenization and reverse tokenization (use stubs/placeholders)
- Full security and harmful-query blocking implementation (assume pre-validated input)

## Business Rule (Source of Truth)
A user is eligible for lottery **only if both are true**:
1. Balance is greater than 50,000
2. Years with bank is 3 or more

## Data Model for Current MVP (Locked)
Use one table for now:

`customer_lottery_profile`
- `user_id` (PK)
- `full_name`
- `balance`
- `years_in_bank`
- `updated_at`

## Phase 1: Define Contracts and State
Goal: lock the data model before coding logic.

Tasks:
- Create shared state schema for the agent graph:
  - user_id
  - original_query
  - normalized_intent
  - balance
  - years_in_bank
  - eligible (bool)
  - decision_reason
  - final_response
- Define strict input/output contract for each agent.

Done when:
- All agent interfaces are documented and consistent.
- Master agent can call each sub-agent with predictable fields.

## Phase 2: Build Savings Agent (Data Fetch Agent)
Goal: fetch facts required for eligibility.

Tasks:
- Implement `savings_agent` with two responsibilities:
  - get_balance(user_id)
  - get_years_in_bank(user_id)
- Add a repository/service layer (or tool function) for MySQL reads from `customer_lottery_profile`.
- Return a structured payload to master agent.

Notes:
- For now, keep tokenization points as TODO hooks.
- If DB is unavailable, support mock mode with static fixtures.

Done when:
- Given `user_id`, agent returns numeric `balance` and `years_in_bank` reliably.

Suggested SQL for this phase:
```sql
SELECT user_id, full_name, balance, years_in_bank, updated_at
FROM customer_lottery_profile
WHERE user_id = %s;
```

## Phase 3: Build Prize Money Agent (Decision Agent)
Goal: evaluate eligibility using only business rules.

Tasks:
- Implement `prize_money_agent` that accepts:
  - balance
  - years_in_bank
- Compute eligibility strictly:
  - eligible = (balance > 50000) and (years_in_bank >= 3)
- Return:
  - eligible
  - decision_reason (human-readable, deterministic)

Done when:
- Edge cases are handled:
  - exactly 50,000 => not eligible
  - exactly 3 years => eligible (if balance condition passes)

## Phase 4: Build Response Agent (User-Facing Output Agent)
Goal: convert decision into clear user message.

Tasks:
- Implement `response_agent` to generate:
  - concise yes/no result
  - reasons for acceptance or rejection
  - optional next-step guidance (for rejected users)
- Keep tone neutral and policy-safe.

Done when:
- Output is stable and understandable for both eligible and non-eligible outcomes.

## Phase 5: Build Master Agent Orchestration
Goal: central workflow controller.

Tasks:
- Master agent flow:
  1. Receive validated query + user_id
  2. Call Savings Agent
  3. Call Prize Money Agent with fetched facts
  4. Call Response Agent with decision context
  5. Return final response
- Add explicit failure handling at each call boundary.
- Log agent transitions for sidebar/debug trace.

Done when:
- One master-agent invocation runs the full chain and returns final answer.

## Phase 6: Wire into LangGraph Workflow
Goal: production-like graph execution.

Tasks:
- Add nodes for master/savings/prize/response.
- Add deterministic edges in exact sequence.
- Define terminal success and failure nodes.

Done when:
- Graph run produces same result as direct orchestrator call.

## Phase 7: API + UI Integration (Minimal)
Goal: connect your agent chain to product surface.

Tasks:
- API endpoint accepts `user_id` + query.
- Endpoint invokes master agent and returns final response.
- UI requirements for this stage:
  - Main panel: query input + response output only
  - Sidebar: agent trace + placeholder tokenization events

Done when:
- User can submit a query and receive eligibility response with agent-step visibility.

## Phase 8: Testing Strategy
Goal: prevent regressions before tokenization/security expansion.

Tasks:
- Unit tests:
  - Savings agent data mapping
  - Prize agent rule correctness
  - Response agent formatting
  - Master orchestration path
- Integration tests:
  - Happy path eligible user
  - Happy path non-eligible user
  - Boundary values (50,000 and 3 years)
  - Missing user / DB error
- E2E test:
  - API request to final response payload

Done when:
- All critical paths pass and decision logic is deterministic.

## Phase 9: Placeholders for Future Tokenization Integration
Goal: make future integration easy without refactor.

Tasks:
- Add interface stubs:
  - `tokenize_payload(data)`
  - `detokenize_payload(data)`
- Call stubs at boundaries where data would be transformed later:
  - Before savings query execution (future detokenize)
  - Before returning facts to master (future tokenize)
  - Before prize evaluation (future detokenize)
- Keep stubs no-op for now.

Done when:
- Current flow works unchanged, and tokenization can be added by replacing stubs.

## Suggested File Ownership for Your Scope
- `orchestrator_app/app/agents/master_agent.py`
- `orchestrator_app/app/agents/savings_agent.py`
- `orchestrator_app/app/agents/prize_money_agent.py`
- `orchestrator_app/app/agents/response_agent.py`
- `orchestrator_app/app/graph/workflow.py`
- `orchestrator_app/app/graph/state.py`
- `orchestrator_app/app/tools/banking_tools.py`

## Minimal DB Contract
- Input: `user_id`
- Output fields required by agents:
  - `balance`
  - `years_in_bank`
- Optional output used by response shaping:
  - `full_name`
  - `updated_at`

## Milestone Sequence (Recommended)
1. Phase 1 + Phase 2
2. Phase 3 + Phase 4
3. Phase 5
4. Phase 6
5. Phase 7
6. Phase 8
7. Phase 9

## Acceptance Checklist
- Master agent orchestrates all sub-agents in correct order.
- Eligibility rule is implemented exactly.
- Final response includes clear reason for yes/no.
- UI shows only input/output in main area and execution trace in sidebar.
- Tokenization is not implemented yet, but extension points exist.
