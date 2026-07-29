from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class CrisisData(BaseModel):
    risk_level: str = "none"
    reason: str = ""
    intervention: str = ""


class EmpathyData(BaseModel):
    emotion: str = "neutral"
    valence: str = "neutral"
    reflection: str = ""


class ClinicalData(BaseModel):
    distortions: list[str] = []
    technique: str = ""
    rag_sources: list[str] = []


class ActionData(BaseModel):
    exercise: str = ""
    instructions: str = ""


class MemoryData(BaseModel):
    past_facts: list[str] = []
    history_summary: str = ""


class AgentResults(BaseModel):
    crisis: CrisisData = CrisisData()
    empathy: EmpathyData = EmpathyData()
    clinical: ClinicalData = ClinicalData()
    memory: MemoryData = MemoryData()
    action: ActionData = ActionData()


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    agents: AgentResults = AgentResults()