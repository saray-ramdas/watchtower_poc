from bilvantis_watchtower.security.enforcement import run_security_gate
from bilvantis_watchtower.types import SecurityLLMGenerator, SecurityState


class Watchtower:
    def __init__(self, llm_generator: SecurityLLMGenerator):
        self._llm_generator = llm_generator

    def run_security_gate(self, state: SecurityState) -> SecurityState:
        return run_security_gate(state, self._llm_generator)

