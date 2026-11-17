import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv


class PostgresDriver:
    """Подключение к PostgreSQL и создание таблиц проекта."""

    def __init__(self):
        env_path = Path(__file__).resolve().parent / ".env"

        if not env_path.exists():
            raise ValueError("Не найден файл .env рядом с драйвером.")

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
            raise ValueError(
                "Заполните параметры в .env: " + ", ".join(missing)
            )

        self.config = {
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "connect_timeout": 10,
        }

        if self.config["dbname"] != "booking":
            raise ValueError(
                "Для проекта VPc07 укажите DB_NAME=booking в .env."
            )

    @contextmanager
    def transaction(self):
        """Открывает транзакцию и гарантирует закрытие соединения."""
        connection = psycopg2.connect(**self.config)

        try:
            with connection:
                with connection.cursor() as cursor:
                    yield cursor
        finally:
            connection.close()

    def create_tables(self):
        """Создаёт таблицы для моделей User, Table и Booking."""
        with self.transaction() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL CHECK (btrim(name) <> ''),
                    email TEXT NOT NULL UNIQUE
                        CHECK (btrim(email) <> '')
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.tables (
                    id SERIAL PRIMARY KEY,
                    number INTEGER NOT NULL UNIQUE
                        CHECK (number > 0),
                    capacity INTEGER NOT NULL
                        CHECK (capacity > 0)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS public.bookings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL
                        REFERENCES public.users(id)
                        ON DELETE RESTRICT,
                    table_id INTEGER NOT NULL
                        REFERENCES public.tables(id)
                        ON DELETE RESTRICT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP NOT NULL,
                    guests INTEGER NOT NULL CHECK (guests > 0),
                    CHECK (end_time > start_time)
                );
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS
                    idx_bookings_table_time
                ON public.bookings (table_id, start_time, end_time);
            """)

    def get_table_names(self):
        """Возвращает список обычных таблиц схемы public."""
        with self.transaction() as cursor:
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            return [row[0] for row in cursor.fetchall()]