from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
