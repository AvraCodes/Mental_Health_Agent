from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.app.agents.base import BaseAgent, AgentInput, AgentOutput

ACTION_PROMPT = """The user seems to be experiencing {emotion}. Suggest one grounding exercise
or actionable step they can do right now (e.g., 5-4-3-2-1 sensory exercise,
deep breathing, journaling prompt, behavioral activation step).

Return JSON:
{{"exercise": "name of exercise", "instructions": "step-by-step instructions (2-3 sentences)"}}

User message: "{message}" """


class ActionAgent(BaseAgent):
    def __init__(self):
        super().__init__("action_resource")

    def run(self, inp: AgentInput) -> AgentOutput:
        emotion = "distress"
        if hasattr(inp, 'context') and inp.context:
            import json as _json
            try:
                parsed = _json.loads(inp.context) if isinstance(inp.context, str) else {}
                emotion = parsed.get("emotion", "distress")
            except Exception:
                pass

        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = ACTION_PROMPT.format(emotion=emotion, message=inp.user_message)
        response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
        import json
        try:
            parsed = json.loads(response.text.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            parsed = {
                "exercise": "deep_breathing",
                "instructions": "Take 5 slow deep breaths. Inhale for 4 seconds, hold for 4, exhale for 4.",
            }

        return AgentOutput(
            agent_name=self.name,
            result=parsed.get("instructions", ""),
            data=parsed,
        )