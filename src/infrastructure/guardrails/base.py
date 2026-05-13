from dataclasses import dataclass, field
from abc import ABC, abstractmethod


@dataclass
class GuardrailResult:
    passed: bool
    reason: str = ""
    status_code: int = 200
    metadata: dict = field(default_factory=dict)


class Guardrail(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def validate(self, query: str, client_ip: str) -> GuardrailResult:
        ...
