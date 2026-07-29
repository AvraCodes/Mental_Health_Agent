from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.app.agents.base import BaseAgent, AgentInput, AgentOutput

CRISIS_KEYWORDS = [
    "kill myself", "want to die", "end my life", "suicide", "not worth living",
    "better off dead", "self-harm", "hurt myself", "can't go on",
    "want to disappear", "no reason to live", "ending it",
]

CRISIS_PROMPT = """You are a crisis triage assessor. Analyze the user's message and determine:

1. **Risk level**: one of [none, low, moderate, high]
2. **Reason**: brief justification (1 sentence)
3. **Intervention**: if risk is moderate or high, suggest an immediate intervention step

User message: "{message}"

Respond in this JSON format (no markdown):
{{"risk_level": "none|low|moderate|high", "reason": "...", "intervention": "..."}}"""


class CrisisAgent(BaseAgent):
    def __init__(self):
        super().__init__("crisis_triage")

    def run(self, inp: AgentInput) -> AgentOutput:
        msg_lower = inp.user_message.lower()

        keyword_hit = any(kw in msg_lower for kw in CRISIS_KEYWORDS)
        if not keyword_hit:
            return AgentOutput(
                agent_name=self.name,
                result="no_crisis_detected",
                data={"risk_level": "none"},
                priority=0,
            )

        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = CRISIS_PROMPT.format(message=inp.user_message)
        response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
        import json
        try:
            parsed = json.loads(response.text.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            parsed = {"risk_level": "moderate", "reason": "Keyword match triggered", "intervention": "Provide crisis resources"}

        risk = parsed.get("risk_level", "moderate")

        if risk == "high":
            return AgentOutput(
                agent_name=self.name,
                result="CRISIS_OVERRIDE",
                data=parsed,
                priority=100,
            )
        if risk == "moderate":
            return AgentOutput(
                agent_name=self.name,
                result="crisis_flagged",
                data=parsed,
                priority=50,
            )
        return AgentOutput(
            agent_name=self.name,
            result="no_crisis_detected",
            data={"risk_level": "none"},
            priority=0,
        )