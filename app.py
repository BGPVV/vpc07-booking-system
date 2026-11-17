import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

import psycopg2

from backend import BookingService


DATE_FORMAT = "%d.%m.%Y %H:%M"


class BookingApp:
    def __init__(self, root, service):
        self.root = root
        self.service = service
        self.forms = {}
        self.trees = {}
        self.selected = {}
        self.records = {}
        self.user_choices = {}
        self.table_choices = {}

        root.title("VPc07 — Мини-система бронирования")
        root.geometry("1150x720")
        root.minsize(950, 650)

        ttk.Label(
            root,
            text="Бронирование столиков",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=15, pady=10)

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=5)

        self.make_tab(
            "users",
            "Пользователи",
            [
                ("name", "Имя", False),
                ("email", "Email", False),
            ],
            [
                ("id", "ID", 60),
                ("name", "Имя", 220),
                ("email", "Email", 320),
            ],
        )

        self.make_tab(
            "tables",
            "Столики",
            [
                ("number", "Номер столика", False),
                ("capacity", "Количество мест", False),
            ],
            [
                ("id", "ID", 60),
                ("number", "Номер столика", 180),
                ("capacity", "Количество мест", 180),
            ],
        )

        self.make_tab(
            "bookings",
            "Бронирования",
            [
                ("user", "Пользователь", True),
                ("table", "Столик", True),
                ("start", "Начало: ДД.ММ.ГГГГ ЧЧ:ММ", False),
                ("end", "Окончание: ДД.ММ.ГГГГ ЧЧ:ММ", False),
                ("guests", "Количество гостей", False),
            ],
            [
                ("id", "ID", 50),
                ("user", "Пользователь", 160),
                ("table", "Столик", 80),
                ("start", "Начало", 160),
                ("end", "Окончание", 160),
                ("guests", "Гостей", 70),
            ],
        )

        self.status = tk.StringVar(value="Готово.")
        ttk.Label(
            root, textvariable=self.status, wraplength=1050
        ).pack(anchor="w", padx=15, pady=10)

        self.refresh()

    def run_action(self, action):
        try:
            action()
        except (ValueError, psycopg2.Error) as error:
            self.status.set(f"Ошибка: {error}")
            messagebox.showerror(
                "Не удалось выполнить действие",
                str(error),
                parent=self.root,
            )

    def make_tab(self, key, title, fields, columns):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text=title)
        self.selected[key] = None
        self.forms[key] = {}

        form = ttk.Frame(tab)
        form.pack(fill="x")

        for row, (field, label, is_combo) in enumerate(fields):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="w", padx=5, pady=4
            )

            if is_combo:
                widget = ttk.Combobox(
                    form, state="readonly", width=48
                )
            else:
                widget = ttk.Entry(form, width=50)

            widget.grid(
                row=row, column=1, sticky="ew", padx=5, pady=4
            )
            self.forms[key][field] = widget

        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(tab)
        buttons.pack(fill="x", pady=10)

        actions = [
            ("Очистить / новая запись", lambda: self.clear_form(key)),
            ("Добавить", lambda: self.save(key, False)),
            ("Сохранить изменения", lambda: self.save(key, True)),
            ("Удалить", lambda: self.delete(key)),
            ("Обновить", self.refresh),
        ]

        if key == "bookings":
            actions.append(
                ("Проверить доступность", self.check_availability)
            )

        for label, action in actions:
            ttk.Button(
                buttons,
                text=label,
                command=lambda fn=action: self.run_action(fn),
            ).pack(side="left", padx=3)

        ttk.Label(
            tab,
            text=(
                "Для изменения или удаления выберите строку в списке. "
                "Для добавления нажмите «Очистить / новая запись»."
            ),
            wraplength=1000,
        ).pack(anchor="w", pady=(0, 8))

        area = ttk.Frame(tab)
        area.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            area,
            columns=[item[0] for item in columns],
            show="headings",
            selectmode="browse",
        )

        for field, label, width in columns:
            tree.heading(field, text=label)
            tree.column(field, width=width, minwidth=45)

        scrollbar = ttk.Scrollbar(
            area, orient="vertical", command=tree.yview
        )
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.bind(
            "<<TreeviewSelect>>",
            lambda event, tab_key=key: self.select_row(tab_key),
        )
        self.trees[key] = tree

    def put(self, key, field, value):
        widget = self.forms[key][field]

        if isinstance(widget, ttk.Combobox):
            widget.set(str(value))
        else:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))

    def clear_form(self, key):
        self.selected[key] = None
        tree = self.trees[key]

        for item in tree.selection():
            tree.selection_remove(item)

        for field in self.forms[key]:
            self.put(key, field, "")

        if key == "bookings":
            self.put(key, "guests", "2")

    def refresh(self):
        # Сначала получаем все данные, затем обновляем интерфейс.
        users = self.service.get_all_users()
        tables = self.service.get_all_tables()
        bookings = self.service.get_all_bookings()

        self.records = {
            "users": {item.id: item for item in users},
            "tables": {item.id: item for item in tables},
            "bookings": {item.id: item for item in bookings},
        }

        self.user_choices = {
            f"{item.id}: {item.name} ({item.email})": item.id
            for item in users
        }
        self.table_choices = {
            f"{item.id}: столик №{item.number}, мест: {item.capacity}": item.id
            for item in tables
        }

        self.forms["bookings"]["user"]["values"] = list(
            self.user_choices
        )
        self.forms["bookings"]["table"]["values"] = list(
            self.table_choices
        )

        for key, tree in self.trees.items():
            for item in tree.get_children():
                tree.delete(item)
            self.clear_form(key)

        for item in users:
            self.trees["users"].insert(
                "", "end", iid=str(item.id),
                values=(item.id, item.name, item.email),
            )

        for item in tables:
            self.trees["tables"].insert(
                "", "end", iid=str(item.id),
                values=(item.id, item.number, item.capacity),
            )

        for item in bookings:
            user = self.records["users"].get(item.user_id)
            table = self.records["tables"].get(item.table_id)

            self.trees["bookings"].insert(
                "", "end", iid=str(item.id),
                values=(
                    item.id,
                    user.name if user else f"ID {item.user_id}",
                    table.number if table else f"ID {item.table_id}",
                    item.start_time.strftime(DATE_FORMAT),
                    item.end_time.strftime(DATE_FORMAT),
                    item.guests,
                ),
            )

        self.status.set(
            f"Пользователей: {len(users)} | "
            f"Столиков: {len(tables)} | "
            f"Бронирований: {len(bookings)}"
        )

    def select_row(self, key):
        selection = self.trees[key].selection()

        if not selection:
            return

        record_id = int(selection[0])
        item = self.records[key].get(record_id)

        if item is None:
            return

        self.selected[key] = record_id

        if key == "users":
            self.put(key, "name", item.name)
            self.put(key, "email", item.email)

        elif key == "tables":
            self.put(key, "number", item.number)
            self.put(key, "capacity", item.capacity)

        else:
            user_label = next(
                (
                    label for label, value in self.user_choices.items()
                    if value == item.user_id
                ),
                "",
            )
            table_label = next(
                (
                    label for label, value in self.table_choices.items()
                    if value == item.table_id
                ),
                "",
            )

            self.put(key, "user", user_label)
            self.put(key, "table", table_label)
            self.put(key, "start", item.start_time.strftime(DATE_FORMAT))
            self.put(key, "end", item.end_time.strftime(DATE_FORMAT))
            self.put(key, "guests", item.guests)

    def value(self, key, field):
        return self.forms[key][field].get().strip()

    def integer(self, key, field, label):
        try:
            return int(self.value(key, field))
        except ValueError:
            raise ValueError(f"{label}: введите целое число.") from None

    def booking_period(self):
        table_label = self.value("bookings", "table")

        if table_label not in self.table_choices:
            raise ValueError("Выберите столик из списка.")

        try:
            start = datetime.strptime(
                self.value("bookings", "start"), DATE_FORMAT
            )
            end = datetime.strptime(
                self.value("bookings", "end"), DATE_FORMAT
            )
        except ValueError:
            raise ValueError(
                "Введите дату и время в формате 20.11.2026 18:00."
            ) from None

        return self.table_choices[table_label], start, end

    def save(self, key, update):
        record_id = self.selected[key]

        if update and record_id is None:
            raise ValueError("Сначала выберите запись в списке.")

        if not update and record_id is not None:
            raise ValueError(
                "Для новой записи нажмите «Очистить / новая запись»."
            )

        if key == "users":
            args = (
                self.value(key, "name"),
                self.value(key, "email"),
            )
            if update:
                self.service.update_user(record_id, *args)
            else:
                self.service.create_user(*args)

        elif key == "tables":
            args = (
                self.integer(key, "number", "Номер столика"),
                self.integer(key, "capacity", "Количество мест"),
            )
            if update:
                self.service.update_table(record_id, *args)
            else:
                self.service.create_table(*args)

        else:
            user_label = self.value(key, "user")

            if user_label not in self.user_choices:
                raise ValueError("Выберите пользователя из списка.")

            table_id, start, end = self.booking_period()
            guests = self.integer(key, "guests", "Количество гостей")

            args = (
                self.user_choices[user_label],
                table_id,
                start,
                end,
                guests,
            )

            if update:
                self.service.update_booking(record_id, *args)
            else:
                self.service.create_booking(*args)

        self.refresh()
        messagebox.showinfo(
            "Готово", "Запись сохранена.", parent=self.root
        )

    def delete(self, key):
        record_id = self.selected[key]

        if record_id is None:
            raise ValueError("Сначала выберите запись в списке.")

        if not messagebox.askyesno(
            "Подтверждение",
            f"Удалить выбранную запись ID {record_id}?",
            parent=self.root,
        ):
            return

        actions = {
            "users": self.service.delete_user,
            "tables": self.service.delete_table,
            "bookings": self.service.delete_booking,
        }
        actions[key](record_id)
        self.refresh()

    def check_availability(self):
        table_id, start, end = self.booking_period()

        available = self.service.check_table_availability(
            table_id,
            start,
            end,
            exclude_booking_id=self.selected["bookings"],
        )

        if available:
            text = (
                "Столик свободен по времени.\n"
                "При сохранении также проверяется количество гостей."
            )
        else:
            text = "Столик занят: есть пересекающееся бронирование."

        if self.selected["bookings"] is not None:
            text += "\nВыбранная редактируемая бронь исключена из проверки."

        self.status.set(text.replace("\n", " "))
        messagebox.showinfo(
            "Доступность столика", text, parent=self.root
        )


def main():
    root = tk.Tk()
    root.withdraw()

    try:
        service = BookingService()
        service.driver.create_tables()
        BookingApp(root, service)
    except (ValueError, psycopg2.Error) as error:
        messagebox.showerror(
            "Ошибка запуска", str(error), parent=root
        )
        root.destroy()
        return

    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    main()