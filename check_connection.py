import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


def main():
    env_path = Path(__file__).resolve().parent / ".env"

    if not env_path.exists():
        print("Не найден файл .env рядом с программой.")
        return

    load_dotenv(env_path, override=True, interpolate=False)

    required = (
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    )
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        print("Заполните параметры в .env:", ", ".join(missing))
        return

    connection = None

    try:
        connection = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            connect_timeout=10,
        )

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT current_database(), current_user;"
                )
                database_name, user_name = cursor.fetchone()

        print("Подключение к PostgreSQL выполнено успешно.")
        print("База данных:", database_name)
        print("Пользователь:", user_name)

        if database_name == "booking":
            print("Проверка базы: OK")
        else:
            print("Проверьте DB_NAME в .env: ожидается booking.")

    except psycopg2.Error as error:
        print("Ошибка подключения:")
        print(str(error).strip())

    finally:
        if connection is not None:
            connection.close()
            print("Соединение закрыто.")


if __name__ == "__main__":
    main()