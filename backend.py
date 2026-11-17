from contextlib import contextmanager
from datetime import datetime

import psycopg2

from models.booking import Booking
from models.table import Table
from models.user import User
from postgres_driver import PostgresDriver


class BookingService:
    """Добавление, чтение, изменение и удаление данных."""

    def __init__(self):
        self.driver = PostgresDriver()

    @contextmanager
    def _write(self):
        """Выполняет изменение данных внутри транзакции."""
        try:
            with self.driver.transaction() as cursor:
                # Общая блокировка для операций изменения
                # через этот класс приложения.
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(7072026);"
                )
                yield cursor

        except psycopg2.errors.UniqueViolation as error:
            raise ValueError(
                "Такой email или номер столика уже существует."
            ) from error

        except (
            psycopg2.errors.ForeignKeyViolation,
            psycopg2.errors.RestrictViolation,
        ) as error:
            raise ValueError(
                "Запись связана с другими данными. "
                "Перед удалением пользователя или столика "
                "удалите его бронирования."
            ) from error

    def _read(self, query, params=()):
        """Выполняет запрос чтения и возвращает строки."""
        with self.driver.transaction() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    @staticmethod
    def _positive(value, label):
        """Проверяет положительное целое число."""
        if type(value) is not int or value <= 0:
            raise ValueError(
                f"{label}: требуется целое число больше 0."
            )

    @staticmethod
    def _user_values(name, email):
        """Проверяет и подготавливает имя и email."""
        name = name.strip()
        email = email.strip().lower()

        if not name:
            raise ValueError("Введите имя пользователя.")

        if (
            email.count("@") != 1
            or any(char.isspace() for char in email)
        ):
            raise ValueError(
                "Введите email в формате name@example.com."
            )

        local, domain = email.split("@")

        if (
            not local
            or "." not in domain
            or any(not part for part in domain.split("."))
        ):
            raise ValueError(
                "Введите email в формате name@example.com."
            )

        return name, email

    @staticmethod
    def _validate_period(start_time, end_time):
        """Проверяет начало и окончание бронирования."""
        if (
            not isinstance(start_time, datetime)
            or not isinstance(end_time, datetime)
        ):
            raise ValueError(
                "Укажите дату и время начала и окончания."
            )

        if (
            start_time.tzinfo is not None
            or end_time.tzinfo is not None
        ):
            raise ValueError(
                "Используйте местное время без часового пояса."
            )

        if end_time <= start_time:
            raise ValueError(
                "Окончание должно быть позже начала."
            )

    @staticmethod
    def _require(cursor, query, params, message):
        """Выполняет запрос, который должен вернуть одну строку."""
        cursor.execute(query, params)
        row = cursor.fetchone()

        if row is None:
            raise ValueError(message)

        return row

    # ---------------------------------------------------------
    # Пользователи
    # ---------------------------------------------------------

    def create_user(self, name, email):
        """Создаёт пользователя."""
        name, email = self._user_values(name, email)

        with self._write() as cursor:
            cursor.execute(
                """
                INSERT INTO public.users (name, email)
                VALUES (%s, %s)
                RETURNING id, name, email;
                """,
                (name, email),
            )
            row = cursor.fetchone()

        return User(
            id=row[0],
            name=row[1],
            email=row[2],
        )

    def get_all_users(self):
        """Возвращает всех пользователей."""
        rows = self._read(
            """
            SELECT id, name, email
            FROM public.users
            ORDER BY id;
            """
        )

        return [
            User(
                id=row[0],
                name=row[1],
                email=row[2],
            )
            for row in rows
        ]

    def update_user(self, user_id, name, email):
        """Изменяет имя и email пользователя."""
        self._positive(user_id, "ID пользователя")
        name, email = self._user_values(name, email)

        with self._write() as cursor:
            row = self._require(
                cursor,
                """
                UPDATE public.users
                SET name = %s, email = %s
                WHERE id = %s
                RETURNING id, name, email;
                """,
                (name, email, user_id),
                "Пользователь не найден.",
            )

        return User(
            id=row[0],
            name=row[1],
            email=row[2],
        )

    def delete_user(self, user_id):
        """Удаляет пользователя, если у него нет бронирований."""
        self._positive(user_id, "ID пользователя")

        with self._write() as cursor:
            self._require(
                cursor,
                """
                DELETE FROM public.users
                WHERE id = %s
                RETURNING id;
                """,
                (user_id,),
                "Пользователь не найден.",
            )

    # ---------------------------------------------------------
    # Столики
    # ---------------------------------------------------------

    def create_table(self, number, capacity):
        """Создаёт столик."""
        self._positive(number, "Номер столика")
        self._positive(capacity, "Количество мест")

        with self._write() as cursor:
            cursor.execute(
                """
                INSERT INTO public.tables (number, capacity)
                VALUES (%s, %s)
                RETURNING id, number, capacity;
                """,
                (number, capacity),
            )
            row = cursor.fetchone()

        return Table(
            id=row[0],
            number=row[1],
            capacity=row[2],
        )

    def get_all_tables(self):
        """Возвращает столики по порядку номеров."""
        rows = self._read(
            """
            SELECT id, number, capacity
            FROM public.tables
            ORDER BY number;
            """
        )

        return [
            Table(
                id=row[0],
                number=row[1],
                capacity=row[2],
            )
            for row in rows
        ]

    def update_table(self, table_id, number, capacity):
        """Изменяет номер и вместимость столика."""
        self._positive(table_id, "ID столика")
        self._positive(number, "Номер столика")
        self._positive(capacity, "Количество мест")

        with self._write() as cursor:
            cursor.execute(
                """
                SELECT COALESCE(MAX(guests), 0)
                FROM public.bookings
                WHERE table_id = %s;
                """,
                (table_id,),
            )
            required_capacity = cursor.fetchone()[0]

            if capacity < required_capacity:
                raise ValueError(
                    "У столика есть бронирование на "
                    f"{required_capacity} гостей. "
                    "Нельзя уменьшить вместимость ниже этого числа."
                )

            row = self._require(
                cursor,
                """
                UPDATE public.tables
                SET number = %s, capacity = %s
                WHERE id = %s
                RETURNING id, number, capacity;
                """,
                (number, capacity, table_id),
                "Столик не найден.",
            )

        return Table(
            id=row[0],
            number=row[1],
            capacity=row[2],
        )

    def delete_table(self, table_id):
        """Удаляет столик, если у него нет бронирований."""
        self._positive(table_id, "ID столика")

        with self._write() as cursor:
            self._require(
                cursor,
                """
                DELETE FROM public.tables
                WHERE id = %s
                RETURNING id;
                """,
                (table_id,),
                "Столик не найден.",
            )

    # ---------------------------------------------------------
    # Доступность столиков
    # ---------------------------------------------------------

    @staticmethod
    def _has_overlap(
        cursor,
        table_id,
        start_time,
        end_time,
        exclude_booking_id=None,
    ):
        """Проверяет пересечение интервалов бронирования."""
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM public.bookings
                WHERE table_id = %s
                  AND start_time < %s
                  AND end_time > %s
                  AND (%s IS NULL OR id <> %s)
            );
            """,
            (
                table_id,
                end_time,
                start_time,
                exclude_booking_id,
                exclude_booking_id,
            ),
        )

        return cursor.fetchone()[0]

    def check_table_availability(
        self,
        table_id,
        start_time,
        end_time,
        exclude_booking_id=None,
    ):
        """Возвращает True, если столик свободен по времени."""
        self._positive(table_id, "ID столика")
        self._validate_period(start_time, end_time)

        if exclude_booking_id is not None:
            self._positive(
                exclude_booking_id,
                "ID бронирования",
            )

        with self.driver.transaction() as cursor:
            self._require(
                cursor,
                """
                SELECT id
                FROM public.tables
                WHERE id = %s;
                """,
                (table_id,),
                "Столик не найден.",
            )

            return not self._has_overlap(
                cursor,
                table_id,
                start_time,
                end_time,
                exclude_booking_id,
            )

    # ---------------------------------------------------------
    # Бронирования
    # ---------------------------------------------------------

    def _save_booking(
        self,
        user_id,
        table_id,
        start_time,
        end_time,
        guests,
        booking_id=None,
    ):
        """Создаёт или изменяет бронь после всех проверок."""
        self._positive(user_id, "ID пользователя")
        self._positive(table_id, "ID столика")
        self._positive(guests, "Количество гостей")
        self._validate_period(start_time, end_time)

        if booking_id is not None:
            self._positive(booking_id, "ID бронирования")

        with self._write() as cursor:
            if booking_id is not None:
                self._require(
                    cursor,
                    """
                    SELECT id
                    FROM public.bookings
                    WHERE id = %s;
                    """,
                    (booking_id,),
                    "Бронирование не найдено.",
                )

            table = self._require(
                cursor,
                """
                SELECT capacity
                FROM public.tables
                WHERE id = %s;
                """,
                (table_id,),
                "Столик не найден.",
            )

            if guests > table[0]:
                raise ValueError(
                    f"У столика только {table[0]} мест. "
                    f"Указано гостей: {guests}."
                )

            self._require(
                cursor,
                """
                SELECT id
                FROM public.users
                WHERE id = %s;
                """,
                (user_id,),
                "Пользователь не найден.",
            )

            if self._has_overlap(
                cursor,
                table_id,
                start_time,
                end_time,
                booking_id,
            ):
                raise ValueError(
                    "Столик занят в выбранное время."
                )

            params = (
                user_id,
                table_id,
                start_time,
                end_time,
                guests,
            )

            if booking_id is None:
                cursor.execute(
                    """
                    INSERT INTO public.bookings (
                        user_id,
                        table_id,
                        start_time,
                        end_time,
                        guests
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    params,
                )
            else:
                cursor.execute(
                    """
                    UPDATE public.bookings
                    SET user_id = %s,
                        table_id = %s,
                        start_time = %s,
                        end_time = %s,
                        guests = %s
                    WHERE id = %s
                    RETURNING id;
                    """,
                    params + (booking_id,),
                )

            saved_id = cursor.fetchone()[0]

        return Booking(
            id=saved_id,
            user_id=user_id,
            table_id=table_id,
            start_time=start_time,
            end_time=end_time,
            guests=guests,
        )

    def create_booking(
        self,
        user_id,
        table_id,
        start_time,
        end_time,
        guests,
    ):
        """Создаёт новое бронирование."""
        return self._save_booking(
            user_id,
            table_id,
            start_time,
            end_time,
            guests,
        )

    def update_booking(
        self,
        booking_id,
        user_id,
        table_id,
        start_time,
        end_time,
        guests,
    ):
        """Изменяет существующее бронирование."""
        return self._save_booking(
            user_id,
            table_id,
            start_time,
            end_time,
            guests,
            booking_id,
        )

    def get_all_bookings(self):
        """Возвращает все бронирования по времени начала."""
        rows = self._read(
            """
            SELECT
                id,
                user_id,
                table_id,
                start_time,
                end_time,
                guests
            FROM public.bookings
            ORDER BY start_time, id;
            """
        )

        return [
            Booking(
                id=row[0],
                user_id=row[1],
                table_id=row[2],
                start_time=row[3],
                end_time=row[4],
                guests=row[5],
            )
            for row in rows
        ]

    def delete_booking(self, booking_id):
        """Удаляет бронирование."""
        self._positive(booking_id, "ID бронирования")

        with self._write() as cursor:
            self._require(
                cursor,
                """
                DELETE FROM public.bookings
                WHERE id = %s
                RETURNING id;
                """,
                (booking_id,),
                "Бронирование не найдено.",
            )