from datetime import datetime

import psycopg2

from backend import BookingService


def main():
    try:
        service = BookingService()

        users = {
            user.email: user
            for user in service.get_all_users()
        }
        tables = {
            table.number: table
            for table in service.get_all_tables()
        }

        if (
            "anna@example.com" not in users
            or "ilya@example.com" not in users
            or 2 not in tables
        ):
            raise ValueError("Сначала запустите seed_data.py.")

        table = tables[2]

        examples = (
            (
                users["anna@example.com"].id,
                datetime(2026, 11, 20, 18, 0),
                datetime(2026, 11, 20, 20, 0),
                2,
            ),
            (
                users["ilya@example.com"].id,
                datetime(2026, 11, 20, 20, 0),
                datetime(2026, 11, 20, 22, 0),
                4,
            ),
        )

        added = 0

        for user_id, start, end, guests in examples:
            existing = service.get_all_bookings()

            already_created = any(
                booking.user_id == user_id
                and booking.table_id == table.id
                and booking.start_time == start
                and booking.end_time == end
                and booking.guests == guests
                for booking in existing
            )

            if not already_created:
                service.create_booking(
                    user_id, table.id, start, end, guests
                )
                added += 1

        print("Добавлено бронирований:", added)
        print()
        print("СПИСОК БРОНИРОВАНИЙ:")

        users_by_id = {
            user.id: user.name for user in users.values()
        }
        tables_by_id = {
            item.id: item.number for item in tables.values()
        }

        bookings = service.get_all_bookings()

        for booking in bookings:
            print(
                f"Бронь {booking.id}: "
                f"{users_by_id[booking.user_id]} | "
                f"столик №{tables_by_id[booking.table_id]} | "
                f"{booking.start_time:%d.%m.%Y %H:%M} — "
                f"{booking.end_time:%H:%M} | "
                f"гостей: {booking.guests}"
            )

        print()
        print("ПРОВЕРКА ДОСТУПНОСТИ СТОЛИКА №2:")

        for start_hour, end_hour in ((19, 21), (22, 23)):
            available = service.check_table_availability(
                table.id,
                datetime(2026, 11, 20, start_hour, 0),
                datetime(2026, 11, 20, end_hour, 0),
            )
            status = "свободен" if available else "занят"
            print(f"{start_hour}:00–{end_hour}:00: {status}")

        print()
        print("Всего бронирований:", len(bookings))
        print("Соединения закрыты.")

    except (psycopg2.Error, ValueError) as error:
        print("Ошибка:")
        print(str(error).strip())


if __name__ == "__main__":
    main()