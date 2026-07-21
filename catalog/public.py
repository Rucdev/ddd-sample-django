"""Public API of the catalog module. Other modules must only import from here."""

import uuid
from dataclasses import dataclass

from catalog.models import Copy, Title


@dataclass(frozen=True)
class TitleDTO:
    id: uuid.UUID
    name: str
    author: str
    isbn: str


@dataclass(frozen=True)
class CopyDTO:
    id: uuid.UUID
    title_id: uuid.UUID
    title_name: str
    copy_number: int
    is_active: bool


def _to_title_dto(title: Title) -> TitleDTO:
    return TitleDTO(id=title.id, name=title.name, author=title.author, isbn=title.isbn)


def _to_copy_dto(copy: Copy) -> CopyDTO:
    return CopyDTO(
        id=copy.id,
        title_id=copy.title_id,
        title_name=copy.title.name,
        copy_number=copy.copy_number,
        is_active=copy.status == Copy.Status.ACTIVE,
    )


def get_title(title_id: uuid.UUID) -> TitleDTO | None:
    title = Title.objects.filter(id=title_id).first()
    return _to_title_dto(title) if title else None


def get_copy(copy_id: uuid.UUID) -> CopyDTO | None:
    copy = Copy.objects.select_related("title").filter(id=copy_id).first()
    return _to_copy_dto(copy) if copy else None
