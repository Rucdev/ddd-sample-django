"""Stand-in for the reservation module's public API until Phase 3 exists.

TODO(Phase 3): replace these calls at the use case call sites with
`reservation.public.get_active_hold_for_copy` and `reservation.public.has_reservation`,
then delete this module.
"""

import uuid


def get_holder_for_copy(copy_id: uuid.UUID) -> uuid.UUID | None:
    """Returns the member_id the copy is held for, or None if it isn't on hold."""
    return None


def has_reservation(title_id: uuid.UUID) -> bool:
    return False
