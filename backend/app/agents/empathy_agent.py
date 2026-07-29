from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.app.agents.base import BaseAgent, AgentInput, AgentOutput

EMPATHY_PROMPT = """Analyze the emotional tone of this message and generate a validating,
empathetic reflection. Return JSON only:

{{
  "emotion": "sad|anxious|angry|fearful|hopeful|neutral|mixed",
  "valence": "positive|negative|neutral",
  "reflection": "A warm, validating reflection statement (one sentence)"
}}

Message: "{message}" """


class EmpathyAgent(BaseAgent):
    def __init__(self):
        super().__init__("empathy")

    def run(self, inp: AgentInput) -> AgentOutput:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = EMPATHY_PROMPT.format(message=inp.user_message)
        response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
        import json
        try:
            parsed = json.loads(response.text.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            parsed = {"emotion": "neutral", "valence": "neutral", "reflection": "I hear you."}
        return AgentOutput(
            agent_name=self.name,
            result=parsed.get("reflection", ""),
            data=parsed,
        )