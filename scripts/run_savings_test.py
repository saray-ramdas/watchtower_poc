import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator_app.app.db.session import SessionLocal
from orchestrator_app.app.agents.savings_agent import run_savings_agent
from orchestrator_app.app.graph.state import build_initial_state


def main() -> None:
    db = SessionLocal()
    try:
        state = build_initial_state("nonexistent_user", "check_savings")
        result = run_savings_agent(state, db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
