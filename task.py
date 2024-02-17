import telebot
import sqlite3

# Подключение к базе данных
def connect_to_db():
    connection = sqlite3.connect("tasks.db")
    return connection

# Список администраторов
ADMINS = [1212068138]

# Список пользователей, ожидающих подтверждения
PENDING_USERS = set()

# Бот
bot = telebot.TeleBot("6734859669:AAFPaSB8FwPPXS7P0dBDFvUj1wPlxPWVsH0")

# Функция проверки администратора
def is_admin(user_id):
    return user_id in ADMINS

# Функция отправки запроса на подтверждение
def send_confirmation_request(user_id):
    bot.send_message(user_id, "Для подтверждения учетной записи отправьте /confirm")

# Обработчик команды /start
@bot.message_handler(commands=["start"])
def start_message(message):
    user_id = message.chat.id
    username = message.chat.username

    # Проверка, зарегистрирован ли пользователь
    with connect_to_db() as connection:
        cursor = connection.cursor()
        cursor.execute("""
        SELECT confirmed FROM users WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

    if result is None:
        # Пользователь не зарегистрирован
        # Добавление пользователя в базу данных
        with connect_to_db() as connection:
            cursor = connection.cursor()
            cursor.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            """, (user_id, username))
            connection.commit()

        PENDING_USERS.add(user_id)
        send_confirmation_request(user_id)
        bot.send_message(message.chat.id, "Ваш запрос на подтверждение учетной записи отправлен администратору.")
    elif result[0] == 0:
        # Пользователь зарегистрирован, но не подтвержден
        bot.send_message(message.chat.id, "Ваш запрос на подтверждение уже отправлен. Пожалуйста, дождитесь ответа.")
    else:
        # Пользователь зарегистрирован и подтвержден
        bot.send_message(message.chat.id, "Вы уже зарегистрированы и можете использовать бота.")

# Обработчик команды /confirm
@bot.message_handler(commands=["confirm"])
def confirm_user(message):
    if not message.text:  # Check if message is empty
        bot.send_message(message.chat.id, "Пожалуйста, введите ID пользователя после команды /confirm.")
        return

    user_id_text = message.text[8:]
    try:
        user_id = int(user_id_text)

        # **Проверка, является ли пользователь администратором:**
        if is_admin(message.from_user.id):
            # **Проверка, что пользователь не пытается подтвердить себя:**
            if user_id != message.from_user.id:
                # Подтверждение пользователя
                with connect_to_db() as connection:
                    cursor = connection.cursor()
                    cursor.execute("""
                    UPDATE users SET confirmed = 1 WHERE user_id = ?
                    """, (user_id,))
                    connection.commit()

                bot.send_message(message.chat.id, f"Учетная запись пользователя @{user_id} подтверждена.")
                bot.send_message(user_id, "Ваша учетная запись подтверждена. Теперь вы можете использовать бота.")
            else:
                bot.send_message(message.chat.id, "Вы не можете подтвердить свою учетную запись.")
        else:
            bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат ID пользователя. Пожалуйста, введите число.")

# **Функция создания задачи:**
@bot.message_handler(commands=["new_task"])
def new_task(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
        return

    # Запрос информации о задаче
    bot.send_message(message.chat.id, "Введите название задачи:")

    # Обработчик ответа на запрос названия
    @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
    def handle_task_name(message):
        task_name = message.text

        # Запрос описания задачи
        bot.send_message(message.chat.id, "Введите описание задачи:")

        # Обработчик ответа на запрос описания
        @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
        def handle_task_description(message):
            task_description = message.text

            # Запрос ID исполнителя
            bot.send_message(message.chat.id, "Введите ID пользователя, который будет исполнять задачу:")

            # Обработчик ответа на запрос ID исполнителя
            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
            def handle_task_assignee(message):
                try:
                    assignee_id = int(message.text)

                    # Проверка, существует ли пользователь
                    with connect_to_db() as connection:
                        cursor = connection.cursor()
                        cursor.execute("""
                        SELECT confirmed FROM users WHERE user_id = ?
                        """, (assignee_id,))
                        result = cursor.fetchone()

                    if result is None:
                        bot.send_message(message.chat.id, "Пользователь с таким ID не найден.")
                        return
                    elif result[0] == 0:
                        bot.send_message(message.chat.id, "Пользователь с таким ID не подтвержден.")
                        return

                    # Запрос приоритета задачи
                    bot.send_message(message.chat.id, "Введите приоритет задачи (от 1 до 5):")

                    # Обработчик ответа на запрос приоритета
                    @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
                    def handle_task_priority(message):
                        try:
                            priority = int(message.text)

                            if 1 <= priority <= 5:
                                # Сохранение задачи в базе данных
                                with connect_to_db() as connection:
                                    cursor = connection.cursor()
                                    cursor.execute("""
                                    INSERT INTO tasks (name, description, assignee_id, priority)
                                    VALUES (?, ?, ?, ?)
                                    """, (task_name, task_description, assignee_id, priority))
                                    connection.commit()

                                bot.send_message(message.chat.id, "Задача успешно создана.")

                                # Уведомление исполнителя о новой задаче
                                bot.send_message(assignee_id, f"Вам назначена новая задача: {task_name}")
                            else:
                                bot.send_message(message.chat.id, "Неверный формат приоритета. Допустимые значения: от 1 до 5.")
                        except ValueError:
                            bot.send_message(message.chat.id, "Неверный формат приоритета. Должно быть число.")

                except ValueError:
                    bot.send_message(message.chat.id, "Неверный формат ID пользователя. Должно быть число.")

# Функция получения списка задач
@bot.message_handler(commands=["get_tasks"])
def get_tasks(message):
    # Проверка, является ли пользователь администратором или исполнителем
    if not is_admin(message.from_user.id):
        with connect_to_db() as connection:
            cursor = connection.cursor()
            cursor.execute("""
            SELECT assignee_id FROM tasks WHERE assignee_id = ?
            """, (message.from_user.id,))
            result = cursor.fetchone()

        if result is None:
            bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
            return

    # Получение списка задач
    with connect_to_db() as connection:
        cursor = connection.cursor()

        if is_admin(message.from_user.id):
            # Все задачи
            cursor.execute("""
            SELECT * FROM tasks
            """)
        else:
            # Задачи, назначенные данному пользователю
            cursor.execute("""
            SELECT * FROM tasks WHERE assignee_id = ?
            """, (message.from_user.id,))

        tasks = cursor.fetchall()

    # Отправка списка задач
    for task in tasks:
        task_id, task_name, task_description, assignee_id, task_priority, task_status = task

        assignee_username = None
        with connect_to_db() as connection:
            cursor = connection.cursor()
            cursor.execute("""
            SELECT username FROM users WHERE user_id = ?
            """, (assignee_id,))
            result = cursor.fetchone()

        if result is not None:
            assignee_username = result[0]

        bot.send_message(message.chat.id, f"**Задача №{task_id}**\n\n"
                         f"Название: {task_name}\n"
                         f"Описание: {task_description}\n"
                         f"Исполнитель: @{assignee_username}\n"
                         f"Приоритет: {task_priority}\n"
                         f"Статус: {task_status}")

# Функция редактирования задачи
@bot.message_handler(commands=["edit_task"])
def edit_task(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
        return

    # Запрос ID задачи
    bot.send_message(message.chat.id, "Введите ID задачи, которую хотите отредактировать:")

    # Обработчик ответа на запрос ID задачи
    @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
    def handle_task_id(message):
        try:
            task_id = int(message.text)

            # Проверка, существует ли задача
            with connect_to_db() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                SELECT * FROM tasks WHERE task_id = ?
                """, (task_id,))
                result = cursor.fetchone()

            if result is None:
                bot.send_message(message.chat.id, "Задача с таким ID не найдена.")
                return

            # Запрос информации о том, что нужно изменить
            bot.send_message(message.chat.id, "Что вы хотите изменить?\n"
                             "1. Название\n"
                             "2. Описание\n"
                             "3. Исполнителя\n"
                             "4. Приоритет\n"
                             "5. Статус")

            # Обработчик ответа на запрос информации о том, что нужно изменить
            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
            def handle_edit_field(message):
                try:
                    edit_field = int(message.text)

                    if 1 <= edit_field <= 5:
                        if edit_field == 1:
                            # Редактирование названия
                            bot.send_message(message.chat.id, "Введите новое название задачи:")

                            # Обработчик ответа на запрос нового названия
                            def handle_new_task_name(message):
                                new_task_name = message.text

                                # Сохранение нового названия
                                with connect_to_db() as connection:
                                    cursor = connection.cursor()
                                    cursor.execute("""
                                    UPDATE tasks SET name = ? WHERE task_id = ?
                                    """, (new_task_name, task_id))
                                    connection.commit()

                                bot.send_message(message.chat.id, "Название задачи успешно изменено.")

                        elif edit_field == 2:
                            # Редактирование описания
                            bot.send_message(message.chat.id, "Введите новое описание задачи:")

                            # Обработчик ответа на запрос нового описания
                            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
                            def handle_new_task_description(message):
                                new_task_description = message.text

                                # Сохранение нового описания
                                with connect_to_db() as connection:
                                    cursor = connection.cursor()
                                    cursor.execute("""
                                    UPDATE tasks SET description = ? WHERE task_id = ?
                                    """, (new_task_description, task_id))
                                    connection.commit()

                                bot.send_message(message.chat.id, "Описание задачи успешно изменено.")

                        elif edit_field == 3:
                            # Редактирование исполнителя
                            bot.send_message(message.chat.id, "Введите ID нового исполнителя задачи:")

                            # Обработчик ответа на запрос нового ID исполнителя
                            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
                            def handle_new_task_assignee(message):
                                try:
                                    new_assignee_id = int(message.text)

                                    # Проверка, существует ли пользователь
                                    with connect_to_db() as connection:
                                        cursor = connection.cursor()
                                        cursor.execute("""
                                        SELECT confirmed FROM users WHERE user_id = ?
                                        """, (new_assignee_id,))
                                        result = cursor.fetchone()

                                    if result is None:
                                        bot.send_message(message.chat.id, "Пользователь с таким ID не найден.")
                                        return
                                    elif result[0] == 0:
                                        bot.send_message(message.chat.id, "Пользователь с таким ID не подтвержден.")
                                        return

                                    # Сохранение нового исполнителя
                                    with connect_to_db() as connection:
                                        cursor = connection.cursor()
                                        cursor.execute("""
                                        UPDATE tasks SET assignee_id = ? WHERE task_id = ?
                                        """, (new_assignee_id, task_id))
                                        connection.commit()

                                    bot.send_message(message.chat.id, "Исполнитель задачи успешно изменен.")

                                except ValueError:
                                    bot.send_message(message.chat.id, "Неверный формат ID пользователя. Должно быть число.")

                        elif edit_field == 4:
                            # Редактирование приоритета
                            bot.send_message(message.chat.id, "Введите новый приоритет задачи (от 1 до 5):")

                            # Обработчик ответа на запрос нового приоритета
                            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
                            def handle_new_task_priority(message):
                                try:
                                    new_priority = int(message.text)

                                    if 1 <= new_priority <= 5:
                                        # Сохранение нового приоритета
                                        with connect_to_db() as connection:
                                            cursor = connection.cursor()
                                            cursor.execute("""
                                            UPDATE tasks SET priority = ? WHERE task_id = ?
                                            """, (new_priority, task_id))
                                            connection.commit()

                                        bot.send_message(message.chat.id, "Приоритет задачи успешно изменен.")

                                    else:
                                        bot.send_message(message.chat.id, "Неверный формат приоритета. Допустимые значения: от 1 до 5.")
                                except ValueError:
                                    bot.send_message(message.chat.id, "Неверный формат приоритета. Должно быть число.")

                        elif edit_field == 5:
                            # Редактирование статуса
                            bot.send_message(message.chat.id, "Введите новый статус задачи (new, in progress, closed):")

                            # Обработчик ответа на запрос нового статуса
                            @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
                            def handle_new_task_status(message):
                              if not is_admin(message.from_user.id):
                                bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
                                return
                            
                              if message.text not in ("new", "in progress", "closed"):
                                bot.send_message(message.chat.id, "Неверный формат статуса. Допустимые значения: new, in progress, closed.")
                                return
                            
                              # Сохранение нового статуса
                              with connect_to_db() as connection:
                                cursor = connection.cursor()
                                cursor.execute("""
                                  UPDATE tasks SET status = ? WHERE task_id = ?
                                """, (message.text, task_id))
                                connection.commit()
                            
                              bot.send_message(message.chat.id, "Статус задачи успешно изменен.")

                    else:
                        bot.send_message(message.chat.id, "Неверный номер пункта.")

                except ValueError:
                    bot.send_message(message.chat.id, "Неверный формат номера пункта. Должно быть число.")

        except ValueError:
            bot.send_message(message.chat.id, "Неверный формат ID задачи. Должно быть число.")

# Функция закрытия задачи
@bot.message_handler(commands=["close_task"])
def close_task(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У вас нет доступа к этой команде.")
        return

    # Запрос ID задачи
    bot.send_message(message.chat.id, "Введите ID задачи, которую хотите закрыть:")

    # Обработчик ответа на запрос ID задачи
    @bot.message_handler(func=lambda message: message.from_user.id == message.chat.id)
    def handle_task_id(message):
        try:
            task_id = int(message.text)

            # Проверка, существует ли задача
            with connect_to_db() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                SELECT * FROM tasks WHERE task_id = ?
                """, (task_id,))
                result = cursor.fetchone()

            if result is None:
                bot.send_message(message.chat.id, "Задача с таким ID не найдена.")
                return

            # Закрытие задачи
            with connect_to_db() as connection:
                cursor = connection.cursor()
                cursor.execute("""
                UPDATE tasks SET status = 'closed' WHERE task_id = ?
                """, (task_id,))
                connection.commit()

            bot.send_message(message.chat.id, "Задача успешно закрыта.")

        except ValueError:
            bot.send_message(message.chat.id, "Неверный формат ID задачи. Должно быть число.")

# **Контроль доступа:**
# - Доступ к командам /new_task, /edit_task, /close_task имеют только администраторы.
# - Доступ к команде /get_tasks имеют администраторы и исполнители, которым назначены задачи.

# **Дополнительные возможности:**
# - Добавление комментариев к задачам.
# - Прикрепление файлов к задачам.
# - Настройка уведомлений о событиях.

# **Тестирование:**
# - Автоматические тесты для проверки функциональности бота.

# **Ограничения:**
# - Максимальное количество задач.
# - Максимальный размер файлов.

# **Безопасность:**
# - Хранение паролей пользователей в зашифрованном виде.
# - Защита от CSRF-атак.

# **Документация:**
# - Подробное описание API бота.

# **Поддержка:**
# - Поддержка пользователей через Telegram.
# - Отслеживание и исправление ошибок.

# **Запуск бота:**
# ```
# python bot.py
# ```

# **Примечания:**
# - Этот код является упрощенным примером.
# - В реальном проекте необходимо добавить проверки на ошибки и обработку исключений.
# - Для обеспечения безопасности необходимо использовать HTTPS и другие меры защиты.

bot.polling()