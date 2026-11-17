from datetime import datetime
from uuid import uuid4

import psycopg2

from backend import BookingService


def expect_rejection(label, action, expected_message):
    """Проверяет, что операция отклонена по ожидаемой причине."""
    try:
        action()
    except ValueError as error:
        if expected_message not in str(error):
            raise RuntimeError(
                f"{label}: получена другая ошибка: {error}"
            ) from error

        print(f"OK — {label}: {error}")
    else:
        raise RuntimeError(
            f"{label}: операция неожиданно разрешена."
        )


def main():
    service = None
    user_id = None
    table_id = None

    try:
        service = BookingService()

        before = (
            len(service.get_all_users()),
            len(service.get_all_tables()),
            len(service.get_all_bookings()),
        )
        print("До проверки (пользователи, столики, брони):", before)

        token = uuid4().hex[:12]

        user = service.create_user(
            "Тестовый пользователь",
            f"crud-{token}@example.com",
        )
        user_id = user.id

        existing_numbers = [
            table.number for table in service.get_all_tables()
        ]
        test_number = max(existing_numbers, default=0) + 100

        table = service.create_table(test_number, 4)
        table_id = table.id

        start = datetime(2026, 11, 21, 18, 0)
        end = datetime(2026, 11, 21, 20, 0)

        booking = service.create_booking(
            user_id, table_id, start, end, 2
        )
        print("OK — пользователь, столик и бронирование созданы.")

        # Проверяем изменение пользователя и чтение из базы.
        service.update_user(
            user_id,
            "Тестовый пользователь — изменён",
            f"crud-{token}@example.com",
        )
        saved_user = next(
            item for item in service.get_all_users()
            if item.id == user_id
        )

        if saved_user.name != "Тестовый пользователь — изменён":
            raise RuntimeError("Изменение пользователя не сохранилось.")

        print("OK — изменение пользователя сохранено.")

        # Проверяем изменение столика.
        service.update_table(table_id, test_number, 6)
        saved_table = next(
            item for item in service.get_all_tables()
            if item.id == table_id
        )

        if saved_table.capacity != 6:
            raise RuntimeError("Изменение столика не сохранилось.")

        print("OK — вместимость столика изменена с 4 до 6.")

        # Та же бронь не должна конфликтовать сама с собой.
        service.update_booking(
            booking.id, user_id, table_id, start, end, 5
        )
        saved_booking = next(
            item for item in service.get_all_bookings()
            if item.id == booking.id
        )

        if saved_booking.guests != 5:
            raise RuntimeError("Изменение бронирования не сохранилось.")

        print("OK — количество гостей изменено с 2 до 5.")

        expect_rejection(
            "Пересекающаяся бронь запрещена",
            lambda: service.create_booking(
                user_id,
                table_id,
                datetime(2026, 11, 21, 19, 0),
                datetime(2026, 11, 21, 21, 0),
                2,
            ),
            "Столик занят",
        )

        expect_rejection(
            "Превышение вместимости запрещено",
            lambda: service.create_booking(
                user_id,
                table_id,
                datetime(2026, 11, 21, 22, 0),
                datetime(2026, 11, 21, 23, 0),
                7,
            ),
            "только 6 мест",
        )

        expect_rejection(
            "Неправильный интервал запрещён",
            lambda: service.create_booking(
                user_id, table_id, end, start, 2
            ),
            "Окончание должно быть позже начала",
        )

        expect_rejection(
            "Уменьшение вместимости ниже числа гостей запрещено",
            lambda: service.update_table(table_id, test_number, 4),
            "Нельзя уменьшить вместимость",
        )

        expect_rejection(
            "Удаление пользователя с бронью запрещено",
            lambda: service.delete_user(user_id),
            "Запись связана",
        )

        expect_rejection(
            "Удаление столика с бронью запрещено",
            lambda: service.delete_table(table_id),
            "Запись связана",
        )

        # Создаём соседнюю бронь: она начинается ровно
        # в момент окончания первой.
        adjacent = service.create_booking(
            user_id,
            table_id,
            datetime(2026, 11, 21, 20, 0),
            datetime(2026, 11, 21, 22, 0),
            2,
        )
        print("OK — соседняя бронь 20:00–22:00 разрешена.")

        expect_rejection(
            "Пересечение при изменении брони запрещено",
            lambda: service.update_booking(
                adjacent.id,
                user_id,
                table_id,
                datetime(2026, 11, 21, 19, 0),
                datetime(2026, 11, 21, 21, 0),
                2,
            ),
            "Столик занят",
        )

        unchanged = next(
            item for item in service.get_all_bookings()
            if item.id == adjacent.id
        )

        if (
            unchanged.start_time != datetime(2026, 11, 21, 20, 0)
            or unchanged.end_time != datetime(2026, 11, 21, 22, 0)
        ):
            raise RuntimeError("Отклонённое изменение затронуло бронь.")

        print("OK — после отказа прежнее время брони сохранено.")

        # Удаляем только созданные этим тестом записи.
        service.delete_booking(adjacent.id)
        service.delete_booking(booking.id)
        service.delete_table(table_id)
        service.delete_user(user_id)

        if any(
            item.id == user_id for item in service.get_all_users()
        ):
            raise RuntimeError("Тестовый пользователь не удалён.")

        if any(
            item.id == table_id for item in service.get_all_tables()
        ):
            raise RuntimeError("Тестовый столик не удалён.")

        if any(
            item.id in (booking.id, adjacent.id)
            for item in service.get_all_bookings()
        ):
            raise RuntimeError("Тестовые бронирования не удалены.")

        print("OK — удаление бронирований, столика и пользователя проверено.")

        after = (
            len(service.get_all_users()),
            len(service.get_all_tables()),
            len(service.get_all_bookings()),
        )
        print()
        print("После проверки:", after)

        if before != after:
            raise RuntimeError("Итоговые количества записей изменились.")

        print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ.")

    except (psycopg2.Error, ValueError, RuntimeError, StopIteration) as error:
        print()
        print("ПРОВЕРКА НЕ ЗАВЕРШЕНА:", error)

    finally:
        # Если проверка остановилась раньше времени,
        # пытаемся убрать оставшиеся тестовые записи.
        if service is not None:
            try:
                if table_id is not None:
                    for item in service.get_all_bookings():
                        if item.table_id == table_id:
                            service.delete_booking(item.id)

                    if any(
                        item.id == table_id
                        for item in service.get_all_tables()
                    ):
                        service.delete_table(table_id)

                if user_id is not None:
                    if any(
                        item.id == user_id
                        for item in service.get_all_users()
                    ):
                        service.delete_user(user_id)

                print("Очистка тестовых записей завершена.")

            except (psycopg2.Error, ValueError) as error:
                print("Не удалось завершить очистку:", error)


if __name__ == "__main__":
    main()