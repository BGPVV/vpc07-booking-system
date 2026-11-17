import psycopg2

from backend import BookingService


def main():
    try:
        service = BookingService()
        service.driver.create_tables()

        existing_emails = {
            user.email for user in service.get_all_users()
        }
        added_users = 0

        for name, email in (
            ("Анна", "anna@example.com"),
            ("Илья", "ilya@example.com"),
            ("Мария", "maria@example.com"),
        ):
            if email not in existing_emails:
                service.create_user(name, email)
                existing_emails.add(email)
                added_users += 1

        existing_numbers = {
            table.number for table in service.get_all_tables()
        }
        added_tables = 0

        for number, capacity in (
            (1, 2),
            (2, 4),
            (3, 6),
        ):
            if number not in existing_numbers:
                service.create_table(number, capacity)
                existing_numbers.add(number)
                added_tables += 1

        users = service.get_all_users()
        tables = service.get_all_tables()

        print("База данных: booking")
        print("Добавлено пользователей:", added_users)
        print("Добавлено столиков:", added_tables)

        print()
        print("ПОЛЬЗОВАТЕЛИ:")

        for user in users:
            print(f"ID {user.id}: {user.name} | {user.email}")

        print()
        print("СТОЛИКИ:")

        for table in tables:
            print(
                f"ID {table.id}: столик №{table.number} | "
                f"мест: {table.capacity}"
            )

        print()
        print("Всего пользователей:", len(users))
        print("Всего столиков:", len(tables))
        print("Заполнение завершено. Соединения закрыты.")

    except (psycopg2.Error, ValueError) as error:
        print("Ошибка заполнения:")
        print(str(error).strip())


if __name__ == "__main__":
    main()