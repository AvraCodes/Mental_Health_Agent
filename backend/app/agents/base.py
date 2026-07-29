from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentInput:
    user_message: str
    session_id: str
    session_history: list[dict] = field(default_factory=list)
    context: str = ""


@dataclass
class AgentOutput:
    agent_name: str
    result: str
    data: dict = field(default_factory=dict)
    priority: int = 0   # higher = more urgent


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, inp: AgentInput) -> AgentOutput:
        ...