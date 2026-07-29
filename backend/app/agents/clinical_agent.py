from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.app.agents.base import BaseAgent, AgentInput, AgentOutput
from backend.rag import search

COGNITIVE_DISTORTIONS = [
    "catastrophizing", "all-or-nothing", "mind reading", "fortune telling",
    "emotional reasoning", "overgeneralization", "labeling", "should statements",
    "personalization", "mental filter", "disqualifying the positive",
]

CLINICAL_PROMPT = """You are a CBT/DBT/ACT specialist. Based on the context and the user's message:

Context: {context}

User: "{message}"

Identify any cognitive distortions present. Suggest one evidence-based technique
from CBT, DBT, or ACT that could help.

Return JSON:
{{"distortions": ["list", "of", "distortions"], "technique": "technique name", "suggestion": "brief suggestion for the user"}}"""


class ClinicalAgent(BaseAgent):
    def __init__(self):
        super().__init__("clinical_reasoning")

    def run(self, inp: AgentInput) -> AgentOutput:
        rag_results = search(inp.user_message, top_k=3)
        context = "\n".join(r["text"][:500] for r in rag_results) if rag_results else ""

        client = genai.Client(api_key=GOOGLE_API_KEY)
        prompt = CLINICAL_PROMPT.format(context=context, message=inp.user_message)
        response = client.models.generate_content(model=LLM_MODEL, contents=prompt)
        import json
        try:
            parsed = json.loads(response.text.strip().removeprefix("```json").removesuffix("```"))
        except Exception:
            parsed = {"distortions": [], "technique": "active_listening", "suggestion": ""}

        return AgentOutput(
            agent_name=self.name,
            result=parsed.get("suggestion", ""),
            data={
                "distortions": parsed.get("distortions", []),
                "technique": parsed.get("technique", ""),
                "rag_sources": [r["source"] for r in rag_results],
            },
        )