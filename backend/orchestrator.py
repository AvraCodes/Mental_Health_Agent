from google import genai
from backend.config import GOOGLE_API_KEY, LLM_MODEL
from backend.app.agents.base import AgentInput
from backend.app.agents.crisis_agent import CrisisAgent
from backend.app.agents.empathy_agent import EmpathyAgent
from backend.app.agents.clinical_agent import ClinicalAgent
from backend.app.agents.memory_agent import MemoryAgent
from backend.app.agents.action_agent import ActionAgent
from backend.app.memory import append_to_session, get_session_history
from backend.models import AgentResults, CrisisData, EmpathyData, ClinicalData, ActionData, MemoryData

_crisis = CrisisAgent()
_empathy = EmpathyAgent()
_clinical = ClinicalAgent()
_memory = MemoryAgent()
_action = ActionAgent()


SYSTEM_PROMPT = """You are a compassionate AI mental health support assistant.
You use evidence-based therapeutic techniques (CBT, DBT, ACT) to support users.
You NEVER diagnose, prescribe medication, or claim to replace a licensed therapist.
If someone is in crisis, you encourage them to contact emergency services or a crisis hotline.
Keep responses warm, empathetic, and grounded in the context provided."""


def synthesize(
    user_message: str,
    empathy_out,
    clinical_out,
    memory_out,
    action_out,
    crisis_out,
) -> str:
    client = genai.Client(api_key=GOOGLE_API_KEY)

    tone = empathy_out.data.get("reflection", "")
    distortions = clinical_out.data.get("distortions", [])
    technique = clinical_out.data.get("technique", "")
    clinical_suggestion = clinical_out.result
    history = memory_out.data.get("history", [])
    past_facts = memory_out.data.get("past_facts", [])
    action_suggestion = action_out.result if action_out.data.get("exercise") else ""

    history_text = ""
    if history:
        history_text = "Recent conversation:\n" + "\n".join(
            f"{m['role']}: {m['content'][:200]}" for m in history
        )

    facts_text = ""
    if past_facts:
        facts_text = "Known about user:\n- " + "\n- ".join(past_facts)

    context_parts = [history_text, facts_text]
    if tone:
        context_parts.append(f"Empathetic reflection to weave in: {tone}")
    if distortions:
        context_parts.append(f"Cognitive distortions detected: {', '.join(distortions)}")
    if technique:
        context_parts.append(f"Suggested therapeutic technique: {technique}")
    if clinical_suggestion:
        context_parts.append(f"Clinical suggestion: {clinical_suggestion}")
    if action_suggestion:
        context_parts.append(f"Action suggestion: {action_suggestion}")

    context = "\n".join(p for p in context_parts if p)

    prompt = f"""Agent analysis:\n{context}\n\nUser: {user_message}\n\nWrite a warm empathetic response. Use the agent insights naturally — do not list them. Be conversational and human."""

    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=prompt,
        config={"system_instruction": SYSTEM_PROMPT},
    )
    return response.text


def generate_reply(user_message: str, session_id: str):
    inp = AgentInput(
        user_message=user_message,
        session_id=session_id,
        session_history=get_session_history(session_id),
    )

    crisis_out = _crisis.run(inp)

    if crisis_out.data.get("risk_level") == "high":
        append_to_session(session_id, "user", user_message)
        append_to_session(session_id, "assistant", crisis_out.data.get("intervention", ""))
        return crisis_out.data.get("intervention", "Please contact emergency services."), AgentResults(
            crisis=CrisisData(**crisis_out.data),
        )

    empathy_out = _empathy.run(inp)
    clinical_out = _clinical.run(inp)
    memory_out = _memory.run(inp)
    action_out = _action.run(inp)

    _memory.post_process(inp)

    reply = synthesize(
        user_message, empathy_out, clinical_out, memory_out, action_out, crisis_out,
    )

    append_to_session(session_id, "assistant", reply)

    return reply, AgentResults(
        crisis=CrisisData(**crisis_out.data),
        empathy=EmpathyData(**empathy_out.data),
        clinical=ClinicalData(**clinical_out.data),
        memory=MemoryData(past_facts=memory_out.data.get("past_facts", [])),
        action=ActionData(**action_out.data),
    )