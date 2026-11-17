from datetime import datetime

from models.user import User
from models.table import Table
from models.booking import Booking


def main():
    user = User(
        name="Анна",
        email="anna@example.com",
        id=1,
    )

    table = Table(
        number=1,
        capacity=4,
        id=1,
    )

    booking = Booking(
        user_id=user.id,
        table_id=table.id,
        start_time=datetime(2026, 11, 20, 18, 0),
        end_time=datetime(2026, 11, 20, 20, 0),
        guests=2,
    )

    print("Пользователь:", user.name)
    print("Email:", user.email)
    print("Столик:", table.number)
    print("Количество мест:", table.capacity)
    print("Гостей:", booking.guests)
    print("Начало:", booking.start_time.strftime("%d.%m.%Y %H:%M"))
    print("Окончание:", booking.end_time.strftime("%d.%m.%Y %H:%M"))
    print()
    print("Все три модели подключены и созданы успешно.")
    print("Это проверка в памяти: данные в PostgreSQL не записывались.")


if __name__ == "__main__":
    main()