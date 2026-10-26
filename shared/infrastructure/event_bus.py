from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from typing import Any, TypeVar

from shared.domain.event import DomainEvent

E = TypeVar("E", bound=DomainEvent)

# ハンドラは購読するイベントの具体型(例: OrderPlaced)を引数に取る。subscribe() で
# event_type と handler の引数型を E で結びつけて検査し、保持するときは型を消して持つ
# (publish は type(event) で引くので、渡るイベントの型はハンドラと必ず一致する)。
_subscribers: dict[type[DomainEvent], list[Callable[[Any], None]]] = defaultdict(list)


def subscribe(event_type: type[E], handler: Callable[[E], None]) -> None:
    _subscribers[event_type].append(handler)


def unsubscribe(event_type: type[E], handler: Callable[[E], None]) -> None:
    handlers = _subscribers.get(event_type)
    if handlers and handler in handlers:
        handlers.remove(handler)


def publish(events: Iterable[DomainEvent]) -> None:
    for event in events:
        for handler in _subscribers[type(event)]:
            handler(event)


@contextmanager
def isolated_subscribers() -> Iterator[None]:
    """テスト用。ブロック内は購読者が空の状態から始まり、抜けると元の購読者に戻る。

    購読者を消すだけにすると、AppConfig.ready() で登録した本番の購読(ordering ↔ kitchen など)
    まで消えてしまい、後から走るテストの結果が実行順に左右される。
    """
    global _subscribers
    saved = _subscribers
    _subscribers = defaultdict(list)
    try:
        yield
    finally:
        _subscribers = saved
