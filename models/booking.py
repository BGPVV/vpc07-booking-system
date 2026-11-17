from dataclasses import dataclass
from datetime import datetime


@dataclass
class Booking:
    """Бронирование столика на определённый интервал времени."""

    user_id: int
    table_id: int
    start_time: datetime
    end_time: datetime
    guests: int
    id: int | None = None