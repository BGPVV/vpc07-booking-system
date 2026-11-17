from dataclasses import dataclass


@dataclass
class User:
    """Пользователь, который бронирует столик."""

    name: str
    email: str
    id: int | None = None