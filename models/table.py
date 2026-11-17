from dataclasses import dataclass


@dataclass
class Table:
    """Столик ресторана."""

    number: int
    capacity: int
    id: int | None = None