from backend.app.agents.base import BaseAgent, AgentInput, AgentOutput
from backend.app.memory import (
    get_session_history,
    append_to_session,
    retrieve_facts,
    store_fact,
)

MEMORY_PROMPT = """Based on this exchange, extract 1-2 key facts about the user that would be
useful for future sessions (triggers, coping mechanisms, important people, etc).
Return as a JSON list of strings:
["fact 1", "fact 2"]

User message: "{message}"
"""


class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("memory_context")

    def run(self, inp: AgentInput) -> AgentOutput:
        history = get_session_history(inp.session_id)
        past_facts = retrieve_facts(inp.session_id, inp.user_message)

        relevant_history = history[-4:] if history else []

        return AgentOutput(
            agent_name=self.name,
            result="",
            data={
                "history": relevant_history,
                "past_facts": past_facts,
            },
        )

    def post_process(self, inp: AgentInput):
        from google import genai
        from backend.config import GOOGLE_API_KEY, LLM_MODEL
        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = MEMORY_PROMPT.format(message=inp.user_message)
        response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
        import json
        try:
            facts = json.loads(response.text.strip().removeprefix("```json").removesuffix("```"))
            if isinstance(facts, list):
                for fact in facts:
                    store_fact(inp.session_id, fact)
        except Exception:
            pass
        append_to_session(inp.session_id, "user", inp.user_message)