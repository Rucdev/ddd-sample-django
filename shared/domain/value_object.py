from dataclasses import dataclass


@dataclass(frozen=True)
class ValueObject:
    """Marker base class for value objects. Subclass as a frozen dataclass to get value equality."""
