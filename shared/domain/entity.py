from typing import Any

from shared.domain.event import DomainEvent


class Entity:
    """Base class for entities and aggregate roots. Identity is by `id`, not attribute values."""

    id: Any

    def __init__(self) -> None:
        self._events: list[DomainEvent] = []

    def record_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events, self._events = self._events, []
        return events

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity) or type(other) is not type(self):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
