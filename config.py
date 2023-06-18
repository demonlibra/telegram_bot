#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ----------------------------- Параметры ------------------------------

# Найти в Telegram бота @BotFather -> /mybots -> Выбрать бота -> API Token
API_TOKEN = ''				# API Token бота
bot_id = API_TOKEN.split(':')[0]														# id бота содержится в API_TOKEN

# Отправить команду /get_chat_id и добавить id в кортеж
chats_id = ('')																			# id разрешённых чатов
admins_id = ()																				# id админов

path_db = 'bot.db'																		# Путь к базе данных sqlite3
path_log = 'bot.log'																		# Путь к файлу log
path_censure = 'censure.txt'															# Путь к словарю ругательств
path_spam = 'spam.txt'																	# Путь к словарю спам фраз
path_spam_new_member = 'spam_new_members.txt'									# Путь к словарю спам фраз для новых участников. Применяется только при проверке нового участника

minutes_for_checkin = 3																	# Минут новому участнику группы для введения проверочной фразы
check_marker = ('маркер1', 'маркер2')												# Ключевые фразы для проверки нового участника группы (использовать только нижний регистр)
minutes_between_checkin = 5															# Минут запрета на повторное подключение к группе после исключения

members_poll_for_ban = 3																# Количество голосов для блокировки пользователя по команде ban
ban_days = 367																				# Дней блокировки пользователя по фильрам и команде ban. Указать > 366 для вечной блокировки.
days_in_group_to_use_ban = 30															# Участнику разрешается использовать ban, если он состоит в группе больше указанного количества дней
days_in_group_can_be_banned = 7														# К участнику можно применить ban, если он в группе меньше заданного количества дней 

statistics_period_days = 7																# Формирование статистики за период (дней)
statistics_time_send = '12:05'														# Время отправки статистики

db_time_clean = '04:00'																	# Время запуска очистки (VACUUM) базы данных

# Отправка миниатюр моделей STL и STEP
path_minirender = 'minirender'														# Путь к minirender https://github.com/aslze/minirender
path_models3d = 'models3d'																# Путь к каталогу сохранения 3d-моделей для создания миниатюр
model3d_max_size_preview = 5*1024*1024												# Максимальный размер файла (байт) модели для создания миниатюры
preview_resolution = 800																# Разрешение изображения миниатюры

can_repeat_info = 10																		# Информационные сообщения могут повторяться после указанного количества сообщений в чате

# Ссылки для команды /help /inf /start
help_links = (
	(('Сайт 1', 'https://site1.ru'), ('Сайт 2', 'https://site2.ru')),
	(('Сайт 3', 'https://site3')),
	(('Сайт 4', 'https://site4.ru'), ('Сайт 5', 'https://site5.ru'), ('Сайт 6', 'https://site6.ru'))
	)

# Информационные сообщения при обнаружении меток в сообщениях 
markers_links = (
	(r'(?i)метка_1', 'site1.ru', f'<a href="https://site1.ru">Сайт 1 site1.ru</a>'),
	(r'(?i)метка_2', 'site2.ru', f'<a href="https://site2.ru">Сайт 2 site2.ru</a>'),
	(r'(?i)метка_3', 'site3.ru', f'<a href="https://site3.ru">Сайт 3 site3.ru</a>')
	)