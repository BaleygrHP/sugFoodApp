from typing import Iterable, List

from .domain import TriageContext, TriageDecision


class TriageStrategy:
    name: str

    async def decide(self, ctx: TriageContext) -> TriageDecision | None:
        raise NotImplementedError


class TriageRegistry:
    def __init__(self, strategies: List[TriageStrategy] | None = None):
        self._strategies = strategies or []

    def __iter__(self) -> Iterable[TriageStrategy]:
        return iter(self._strategies)

    def add(self, strategy: TriageStrategy) -> None:
        self._strategies.append(strategy)


def build_default_triage_registry(strategies: List[TriageStrategy] | None = None) -> TriageRegistry:
    return TriageRegistry(strategies or [])
