from unittest import TestCase

from shared.domain.entity import Entity
from shared.domain.event import DomainEvent


class _DummyEvent(DomainEvent):
    pass


class _DummyEntity(Entity):
    def __init__(self, id: int) -> None:
        super().__init__()
        self.id = id


class EntityEqualityTests(TestCase):
    def test_same_type_and_id_are_equal(self) -> None:
        self.assertEqual(_DummyEntity(id=1), _DummyEntity(id=1))

    def test_different_id_are_not_equal(self) -> None:
        self.assertNotEqual(_DummyEntity(id=1), _DummyEntity(id=2))

    def test_different_type_same_id_are_not_equal(self) -> None:
        class _OtherEntity(Entity):
            def __init__(self, id: int) -> None:
                super().__init__()
                self.id = id

        self.assertNotEqual(_DummyEntity(id=1), _OtherEntity(id=1))

    def test_hash_is_based_on_type_and_id(self) -> None:
        self.assertEqual(hash(_DummyEntity(id=1)), hash(_DummyEntity(id=1)))


class EntityEventCollectionTests(TestCase):
    def test_collect_events_returns_recorded_events_and_clears_them(self) -> None:
        entity = _DummyEntity(id=1)
        event = _DummyEvent()
        entity.record_event(event)

        collected = entity.collect_events()

        self.assertEqual(collected, [event])
        self.assertEqual(entity.collect_events(), [])
