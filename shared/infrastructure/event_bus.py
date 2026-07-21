from collections import defaultdict
from collections.abc import Callable, Iterable
from typing import TypeVar

from shared.domain.event import DomainEvent

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[DomainEvent], None]

_subscribers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)


def subscribe(event_type: type[E], handler: Handler) -> None:
    _subscribers[event_type].append(handler)


def publish(events: Iterable[DomainEvent]) -> None:
    for event in events:
        for handler in _subscribers[type(event)]:
            handler(event)


def clear_subscribers() -> None:
    _subscribers.clear()
