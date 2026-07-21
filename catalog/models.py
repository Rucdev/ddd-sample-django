import uuid

from django.db import models


class Title(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, unique=True)

    def __str__(self) -> str:
        return f"{self.name} / {self.author}"


class Copy(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "所蔵中"
        WITHDRAWN = "WITHDRAWN", "除籍"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.ForeignKey(Title, on_delete=models.PROTECT, related_name="copies")
    copy_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["title", "copy_number"], name="unique_copy_number_per_title"
            )
        ]

    def __str__(self) -> str:
        return f"{self.title.name} #{self.copy_number}"
