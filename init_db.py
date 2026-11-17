import psycopg2

from postgres_driver import PostgresDriver


def main():
    try:
        driver = PostgresDriver()
        driver.create_tables()
        table_names = driver.get_table_names()

        print("База данных: booking")
        print("Создание таблиц завершено.")
        print()
        print("Таблицы в схеме public:")

        for name in table_names:
            print("-", name)

        expected = {"users", "tables", "bookings"}

        if expected.issubset(set(table_names)):
            print()
            print("Проверка: все три таблицы существуют.")
        else:
            print()
            print("Проверка: некоторые таблицы отсутствуют.")

        print("Соединения закрыты.")

    except (psycopg2.Error, ValueError) as error:
        print("Ошибка инициализации:")
        print(str(error).strip())


if __name__ == "__main__":
    main()