from sqlalchemy.orm import Session
from langgraph.graph import END, START, StateGraph

from ..agents.master_agent import run_master_agent
from ..agents.prize_money_agent import run_prize_money_agent
from ..agents.response_agent import run_response_agent
from ..agents.savings_agent import run_savings_agent
from .state import EligibilityState


def _node_master(state: EligibilityState) -> EligibilityState:
    return run_master_agent(state)


def _node_savings(state: EligibilityState, db: Session) -> EligibilityState:
    return run_savings_agent(state, db)


def _node_prize_money(state: EligibilityState) -> EligibilityState:
    return run_prize_money_agent(state)


def _node_response(state: EligibilityState) -> EligibilityState:
    return run_response_agent(state)


def _after_master(state: EligibilityState) -> str:
    if state.get("guardrail_status") == "blocked":
        return "response"
    return "savings"


def _after_savings(state: EligibilityState) -> str:
    if state.get("decision_reason") == "user_not_found":
        return "end"
    if state.get("normalized_intent") == "lottery_eligibility":
        return "prize_money"
    state["decision_reason"] = "savings_data_answered_requested_intent"
    return "response"


def _build_workflow(db: Session):
    graph = StateGraph(EligibilityState)

    graph.add_node("master", _node_master)
    graph.add_node("savings", lambda s: _node_savings(s, db))
    graph.add_node("prize_money", _node_prize_money)
    graph.add_node("response", _node_response)

    graph.add_edge(START, "master")
    graph.add_conditional_edges(
        "master",
        _after_master,
        {
            "savings": "savings",
            "response": "response",
        },
    )
    graph.add_conditional_edges(
        "savings",
        _after_savings,
        {
            "prize_money": "prize_money",
            "response": "response",
            "end": END,
        },
    )
    graph.add_edge("prize_money", "response")
    graph.add_edge("response", END)

    return graph.compile()


def run_workflow(state: EligibilityState, db: Session) -> EligibilityState:
    """
    LangGraph Phase 6 workflow wiring.

    Node order:
    master -> savings -> (optional prize_money) -> response -> end
    """
    app = _build_workflow(db)
    result = app.invoke(state)
    return result
