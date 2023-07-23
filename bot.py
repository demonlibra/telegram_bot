#!/usr/bin/env python
# -*- coding: utf-8 -*-

# ======================================================================

# --------------------------- Импорт библиотек -------------------------

import config																				# Файл с параметрами config.py

import time
import re																					# Библиотека регулярных выражений
import schedule																			# Библиотека выполнения задач по расписанию
from threading import Thread															# Библиотека потоков
import sqlite3																				# Библиотека базы данных SQLite3
import os
import sys
import string
import subprocess

from multicolorcaptcha import CaptchaGenerator									# https://pypi.org/project/multicolorcaptcha/

import telebot																				# https://pypi.org/project/pyTelegramBotAPI/
bot = telebot.TeleBot(config.API_TOKEN)
from telebot import version
 
# ======================================================================


# -------------------------- Поток 1 - Бот -----------------------------
def run_Bot():
	bot.infinity_polling(interval=1, timeout=30)
 
# ------------------- Поток 2 - Задачи по расписанию -------------------
def run_Schedulers():																		
	schedule.every().sunday.at(config.statistics_time_send).\
		do(statistics_send, chat_id=config.chats_id[0])							# Отправка статистики
	
	schedule.every().monday.at(config.db_time_clean).\
		do(db_clean)																		# Очистка базы данных
	
	while True:
		schedule.run_pending()
		time.sleep(10)

# -------------------- Получение абсолютного пути ----------------------
def get_full_path(path):
	full_path = os.path.abspath(path)
	if	os.path.exists(full_path):
		return full_path
	else:
		log(f'Ошибка - Файл {full_path} не найден')

# -------------------- Получить множество из файла ---------------------
def set_from_file(path):
	words = set()
	line_number = 0

	with open(path, encoding='utf-8') as file:
		while True:
			line_number += 1
			line = file.readline()
			if not line:			# Остановить обработку, если строка не получена, т.е. это конец файла
				break
			elif line.strip():	# Если строка не пустая
				words.add(line.strip().lower())
			else:
				log(f'Пустая строка {line_number} в файле {path}')

	if not words:
		log(f'Ошибка - Пустой список слов из файла {path}')

	return words

# ------------------------ Запись журнала ------------------------------
def log(log_text, chat_id=False, message_id=False):
	time_marker = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
	print(f'\n{time_marker} {log_text}')											# Вывод сообщения в консоль

											# Запись сообщения в файл 
	if chat_id: log_chat_id = f' в группе {chat_id}'
	else: log_chat_id = ''
	if message_id: log_message_id = f' - {message_id}'
	else: log_message_id = ''
			
	with open (path_log, 'a') as file:
		file.write(f'\n{time_marker} {log_text}{log_chat_id}{log_message_id}')

	table_name = 'log'
	sqlite_query = f"INSERT INTO {table_name} (chat_id, message_id, log_text, unix_time) VALUES ({chat_id}, {message_id}, '{log_text}', {int(time.time())})"
	try:																						# Запись сообщения в базу данных 
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
	except sqlite3.Error as error:
		print(f'Ошибка записи данных в таблицу log {error}')

	if 'ошибка' in log_text.casefold():
		try:
			bot.send_message(config.admins_id[0], log_text)
		except Exception:
			print(f'Не удалось отправить уведомление об ошибке админу')

# -------------------- Поиск записи log с меткой -----------------------
def log_marker_last_id(chat_id, marker):
	table_name = 'log'
	sqlite_query = f"SELECT max(message_id) FROM {table_name} WHERE chat_id=={chat_id} AND log_text LIKE '%{marker}%'"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.row_factory = lambda cursor, row: row[0]	# Вывод только первого элемента вместо кортежа
			cursor.execute(sqlite_query)
			record = cursor.fetchone()
	except Exception:
		log(f'Ошибка получения id сообщения из log по метке {marker}', chat_id)
	else:
		if record:
			return record
		else:
			return 0

# ------------------------ Проверка прав админа ------------------------
def is_admin(chat_id, user_id):
	try:
		member_raw_data = bot.get_chat_member(chat_id, user_id)
	except Exception:
		log(f'Ошибка получения данных пользователя {message.from_user.id}', message.chat.id)
	else:
		if member_raw_data.can_restrict_members or member_raw_data.status == 'creator':
			return True
		else:
			return False

# -------------------------- Проверка группы ---------------------------
def is_group_allowed(message, type=None):
	if (message.chat.id == message.from_user.id):								# Сообщение лично боту
		log(f'Сообщение боту от {member_info(message.from_user)}: {message.text}', message.chat.id, message.id)

		if type == 'handler_help' or type == 'handler_cens':
			return True
		elif not (message.from_user.id in config.admins_id):
			text = f'И что?\nЕхай ...'
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')	# Отправка злых матюков
			except Exception:
				log(f'Ошибка отправки личного недовольства', message.chat.id)
			return False

	elif not (str(message.chat.id) in config.chats_id):						# Если id отсутствует в списке разрешённых групп
		log(f'Обнаружено присутствие в чужой группе ', message.chat.id, message.id)

		try:
			chat_info = bot.get_chat(message.chat.id)
		except Exception:
			log(f'Ошибка получения данных чужой группы', message.chat.id)
		else: log(chat_info)

		text = (
			f'Какого ... ? Я Ваш чат трубу шатал. Мне здесь не нравится. '
			f'Бывайте, Ихтиандры ...\n	\U0001F4A9 \U0001F4A9 \U0001F4A9')
		try:
			bot.send_message(message.chat.id, text, parse_mode='html')		# Отправка злых матюков
		except Exception:
			log(f'Ошибка отправки недовольства', message.chat.id)
		
		try:
			bot.leave_chat(message.chat.id) 											# Выход из чужой группы
		except Exception:
			log(f'Ошибка выхода из группы', message.chat.id)
		
		try:			
			bot_raw_data = bot.get_chat_member(message.chat.id, config.bot_id)	# Получение данных бота
		except Exception:
			bot_name = config.bot_id
			log(f'Ошибка получения данных бота {config.bot_id}', message.chat.id, message.id)
		else:
			bot_name = bot_raw_data.user.username

		text = (
			f'Обнаружено присутствие бота <b>@{bot_name}</b> '
			f'в чужой группе\n{message.chat.id}\n{message.chat.username}')
		try:
			bot.send_message(config.admins_id[0], text, parse_mode='html')	# Отправка уведомления админу
		except Exception:
			log(f'Ошибка отправки уведомления о добавлении бота в чужую группу', message.chat.id)
		return False

	else: return True	# Группа разрешена

# ---------------------------- База данных -----------------------------
def db_initialization():
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()

			# messages - сообщения
			sqlite_create_table_query = """CREATE TABLE IF NOT EXISTS messages (
												id INTEGER PRIMARY KEY AUTOINCREMENT,
												chat_id INTEGER NOT NULL,
												message_id INTEGER NOT NULL,
												from_user_id INTEGER NOT NULL,
												unix_time INTEGER NOT NULL);"""
			cursor.execute(sqlite_create_table_query)

			# members - участники группы
			sqlite_create_table_query = """CREATE TABLE IF NOT EXISTS members (
												id INTEGER PRIMARY KEY AUTOINCREMENT,
												chat_id INTEGER NOT NULL,
												user_id INTEGER NOT NULL,
												time_joined INTEGER NOT NULL,
												time_checkin INTEGER DEFAULT 0,
												time_blocked INTEGER DEFAULT 0);"""
			cursor.execute(sqlite_create_table_query)

			# ban_vote - голосование для блокировки
			sqlite_create_table_query = """CREATE TABLE IF NOT EXISTS ban_vote (
												id INTEGER PRIMARY KEY AUTOINCREMENT,
												chat_id INTEGER NOT NULL,
												user_banned_id INTEGER NOT NULL,
												user_voted_id INTEGER NOT NULL,
												unix_time INTEGER NOT NULL);"""
			cursor.execute(sqlite_create_table_query)

			# log - журнал
			sqlite_create_table_query = """CREATE TABLE IF NOT EXISTS log (
												id INTEGER PRIMARY KEY AUTOINCREMENT,
												chat_id INTEGER,
												message_id INTEGER,
												log_text TEXT NOT NULL,
												unix_time INTEGER NOT NULL);"""
			cursor.execute(sqlite_create_table_query)

	except sqlite3.Error as error:
		log(f'Ошибка подключения базы данных {path_db} {error}')
	else:
		log(f'Подключена база данных {path_db}')

# ----------------------- Очистка базы данных --------------------------
def db_clean():
	db_delete_old_data('log', 'unix_time', 365)
	
	size_before_clean = os.path.getsize(path_db)
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			sqlite_query = f'VACUUM'
			cursor.execute(sqlite_query)
		size_difference = size_before_clean - os.path.getsize(path_db)
	except sqlite3.Error as error:
		log(f'Ошибка очистки базы данных {error}')
	else:
		log(f'Выполнена очистка (-{size_difference} байт) базы данных {path_db}')

# ------------------ Удаление старых строк из таблицы ------------------
def db_delete_old_data(table, time_field, days2del):							# (<имя_таблицы>, <имя_поля_временной_метки>, <удалять_записи_старше_дней>)
	unix_time = time.time() - (days2del * 24 * 60 * 60)
	sqlite_query = f'DELETE FROM {table} WHERE {time_field}<{unix_time}'
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
			number_deleted = cursor.rowcount
	except sqlite3.Error as error:
		log(f'Ошибка удаления старых записей из таблицы {table}, {error}')
	else:
		date = time.strftime("%d-%m-%Y", time.localtime(unix_time))
		log(f'Удалено {number_deleted} строк в таблице {table} старше {date}')

# ----------- Добавление нового участника в таблицу members ------------
def member_add_new(chat_id, user_id, time_joined):
	table_name = 'members'
	sqlite_query = f"INSERT INTO {table_name} (chat_id, user_id, time_joined) VALUES ({chat_id}, {user_id}, {time_joined})"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
	except sqlite3.Error as error:
		log(f'Ошибка добавления нового участника в таблицу members {user_id} {error}', chat_id)
			
# --------------------- Проверка нового участника ----------------------
def member_checkin(chat_id, user_id):
	table_name = 'members'
	sqlite_query = f"SELECT time_checkin, time_joined FROM {table_name} WHERE chat_id=={chat_id} AND user_id=={user_id} ORDER BY id DESC"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
			record = cursor.fetchone()

		if record:
			if record[0] == 0:
				user_checked = False
			else:
				user_checked = True
			time_joined = record[1]	# [time_checkin, time_joined]
		else:
			user_checked = None
			time_joined = 0

		return user_checked, time_joined

	except sqlite3.Error as error:
		log(f'Ошибка получения состояния участника {user_id} {error}', chat_id)
		
# ----------- Количество неудачных проверок нового участника -----------
def member_false_checkin_count(chat_id, user_id, period=time.time()/(24*60*60)):
	table_name = 'members'
	sqlite_query = f"SELECT count(time_joined) FROM {table_name} WHERE chat_id=={chat_id} AND user_id=={user_id} AND time_checkin==0 AND time_joined>{time.time()-period*24*60*60}"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.row_factory = lambda cursor, row: row[0]	# Вывод только первого элемента вместо кортежа
			cursor.execute(sqlite_query)
			number = cursor.fetchone()
		return number
	except sqlite3.Error as error:
		log(f'Ошибка получения количества неудачных проверок {user_id} {error}', chat_id)
	
# ----------------------- Данные пользователя --------------------------
def member_info(user_data):
	return f'{user_data.id} @{user_data.username} {user_data.first_name} {user_data.last_name}'

# -------- Запись времени прохождения проверки новым участником --------
def member_set_checked(chat_id, user_id):
	table_name = 'members'
	sqlite_query = f"UPDATE {table_name} SET time_checkin={int(time.time())} WHERE id==(SELECT max(id) FROM {table_name} WHERE chat_id=={chat_id} AND user_id=={user_id})"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
	except sqlite3.Error as error:
		log(f'Ошибка записи времени прохождения проверки новым участником {user_id} {error}', chat_id)

# -------------------------- Блокировка участника ----------------------
def block_member(chat_id, user_id, period_block=config.ban_days*24*60*60):
	time_now = int(time.time())
	try:
		bot.ban_chat_member(chat_id, user_id, until_date=time_now+period_block)
	except Exception:
		log(f'Ошибка блокировки участника {user_id}', chat_id)
	else:
		if period_block >= config.ban_days*24*60*60:
			log(f'Заблокирован участник {user_id}', chat_id)

			table_name = 'members'
			sqlite_query = f"UPDATE members SET time_blocked={time_now} WHERE id==(SELECT max(id) FROM {table_name} WHERE chat_id=={chat_id} AND user_id=={user_id})"
			try:
				with sqlite3.connect(path_db) as sqlite_connection:
					cursor = sqlite_connection.cursor()
					cursor.execute(sqlite_query)
			except sqlite3.Error as error:
				log(f'Ошибка записи времени блокировки участника {user_id} {error}', chat_id)

# -------------------- Добавление голоса за ban ------------------------
def ban_vote_add(chat_id, user_banned_id, user_voted_id):
	time_now = int(time.time())
	table_name = 'ban_vote'
	sqlite_query = f"INSERT INTO {table_name} (chat_id, user_banned_id, user_voted_id, unix_time) VALUES ({chat_id}, {user_banned_id}, {user_voted_id}, {time_now})"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)			
	except sqlite3.Error as error:
		log(f'Ошибка записи {user_banned_id} в таблицу ban {error}', chat_id)

# ------------- Получение списка проголосовавших за ban ----------------
def ban_voted_get_list(chat_id, banned_id, ban_init_time):
	table_name = 'ban_vote'
	sqlite_query = f"SELECT user_voted_id FROM {table_name} WHERE chat_id=={chat_id} AND user_banned_id=={banned_id} AND unix_time>={ban_init_time}"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.row_factory = lambda cursor, row: row[0]
			cursor.execute(sqlite_query)
			records = cursor.fetchall()
	except sqlite3.Error as error:
		log(f'Ошибка получения списка голосовавших за ban {banned_id} {error}', chat_id)
	else:
		return records

# ------------------ Вставка данных в таблицу messages -----------------
def messages_add_new(message):
	table_name = 'messages'
	sqlite_query = f"INSERT INTO {table_name} (chat_id, message_id, from_user_id, unix_time) VALUES ({message.chat.id}, {message.id}, {message.from_user.id}, {message.date})"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.execute(sqlite_query)
	except sqlite3.Error as error:
		log(f'Ошибка записи данных в таблицу messages о сообщении {message.id} от {member_info(message.from_user)} {error}', message.chat.id, message.id)

# ---------------- Удаление сообщений участника группы ------------------ 
def messages_delete(chat_id, from_user_id):
	table_name = 'messages'
	sqlite_query = f"SELECT message_id FROM {table_name} WHERE chat_id=={chat_id} AND from_user_id=={from_user_id} AND unix_time>{time.time()-2*24*60*60}"
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.row_factory = lambda cursor, row: row[0]	# Вывод только первого элемента вместо кортежа
			cursor.execute(sqlite_query)
			list_messages_id = cursor.fetchall()									# Необработанный список сообщений пользователя
	except sqlite3.Error as error:
		log(f'Ошибка получения списка сообщений пользователя {from_user_id} {error}', chat_id)
	else:
		for message_id in list_messages_id:
			try:
				bot.delete_message(chat_id, message_id)						# Удалить сообщение
				log(f'Удалено сообщение {message_id}', chat_id, message_id)
			except Exception:
				log(f'Ошибка удаления сообщения {message_id}', chat_id, message_id)

# ---------------------- Статистика работы бота ------------------------
def statistics_send(chat_id, period=config.statistics_period_days):
	try:
		with sqlite3.connect(path_db) as sqlite_connection:
			cursor = sqlite_connection.cursor()
			cursor.row_factory = lambda cursor, row: row[0]	# Вывод только первого элемента вместо кортежа
			
			# Прошли проверку за период
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_checkin!=0 AND time_joined>{time.time()-period*24*60*60}"
			cursor.execute(sqlite_query)
			number_checked = cursor.fetchone()
			
			# Не прошли проверку за период
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_checkin==0 AND time_joined>{time.time()-period*24*60*60}"
			cursor.execute(sqlite_query)
			number_kicked = cursor.fetchone()

			# Всего не пропущено
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_checkin==0"
			cursor.execute(sqlite_query)
			number_kicked_all = cursor.fetchone()

			# Всего прошли проверку
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_checkin==1"
			cursor.execute(sqlite_query)
			number_checked_all = cursor.fetchone()
			
			# Дата начала работы бота
			sqlite_query = f"SELECT min(time_joined) FROM members WHERE chat_id=={chat_id}"
			cursor.execute(sqlite_query)
			record = cursor.fetchone()
			date_start_bot = time.strftime("%d-%m-%Y", time.localtime(record))

			# Заблокировано за период
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_blocked>{time.time()-period*24*60*60}"
			cursor.execute(sqlite_query)
			number_blocked = cursor.fetchone()

			# Всего заблокировано
			sqlite_query = f"SELECT count(id) FROM members WHERE chat_id=={chat_id} AND time_blocked!=0"
			cursor.execute(sqlite_query)
			number_blocked_all = cursor.fetchone()

			# Общее количество сообщений и суффикс
			sqlite_query = f"SELECT max(message_id) FROM messages WHERE chat_id=={chat_id}"
			cursor.execute(sqlite_query)
			last_message_id = cursor.fetchone()
			if last_message_id < 1000:
				total_messages = last_message_id
			elif last_message_id > 1000 and last_message_id < 999999:
				total_messages = f'{str(last_message_id)[:-3]}.{str(last_message_id)[-3:-2]}K'
			elif last_message_id > 999999:
				total_messages = f'{str(last_message_id)[:-6]}.{str(last_message_id)[-6:-5]}M'

		#sqlite_connection.close()				# Почему-то с fetchone(), если не закрыть, то появляется ошибка database is locked
	
	except sqlite3.Error as error:
		log(f'Ошибка получения статистики из базы данных {error}', chat_id)

	try:
		chat_member_count = bot.get_chat_member_count(chat_id)
	except Exception:
		log(f'Ошибка получения количества участников группы', chat_id)

	if period == 7:
		text_heading = f'За неделю:'
	elif period == 30 or period == 31:
		text_heading = f'За месяц:'
	elif period == 365 or period == 366:
		text_heading = f'За год:'
	else:
		text_heading = (
		f'В период с {time.strftime("%d-%m-%Y", time.localtime(time.time()-period*24*60*60))}'
		f' по {time.strftime("%d-%m-%Y", time.localtime())}:')

	text = (
		f'{text_heading}'
		f'\n   - nрошло проверку <b>{number_checked}</b> из <b>{number_kicked+number_checked}</b>'
		f'\n   - заблокировано <b>{number_blocked}</b>'
		f'\nВсего с {date_start_bot} по {time.strftime("%d-%m-%Y", time.localtime())}'
		f'\n   - nрошло проверку <b>{number_checked_all}</b> из <b>{number_kicked_all+number_checked_all}</b>'
		f'\n   - заблокировано <b>{number_blocked_all}</b>'
		f'\nВсего участников в группе <b>{chat_member_count}</b>'
		f'\nВсего сообщений <b>{total_messages}</b>')

	try:
		bot.send_message(chat_id, text, parse_mode='html')
	except Exception:
		log(f'Ошибка отправки статистики {error}', chat_id)

# ---------------- Удаление записи из списка captcha -------------------
def captcha_del_records(chat_id, user_id):
	global captcha_list
	for captcha_record in captcha_list[::-1]:										# Поиск в списке captcha для данного пользователя
		if captcha_record['chat_id'] == chat_id and captcha_record['user_id'] == user_id:
			try:
				bot.delete_message(chat_id, captcha_record['captcha_id'])	# Удалить сообщение с изображением captcha
			except Exception:
				log(f'Ошибка удаления captcha с id {captcha_record["captcha_id"]}', chat_id, captcha_record["captcha_id"])
			else:
				captcha_list.remove(captcha_record)
				#log(f"Удалена captcha {captcha_record['captcha']} с id {captcha_record['captcha_id']}", chat_id, captcha_record['captcha_id'])

# ======================================================================

# Не включать для штатного использования, т.к. это большая дыра в безопасности.
# Если бот запущен с root правами, то это позволит выполнить код в системе с root правами.

# ============================= /raw_command ===========================

# @bot.message_handler(commands=['raw_command'])									# Выполняется, если сообщение содержит команду /raw_command
# def handler_raw_command(message):
	# try:																						# Получаем данные участника отправившего запрос /raw_command
		# member_raw_data = bot.get_chat_member(message.chat.id, message.from_user.id)
	# except Exception:
		# log(f'Ошибка получения данных пользователя {message.from_user.id}', message.chat.id)
	# else:
		# if not member_raw_data.can_restrict_members and member_raw_data.status != 'creator':	# Если не разрешена блокировка других участников группы и не основатель группы 
			# log(f'Запрос /raw_command не от администратора группы {member_info(message.from_user)}', message.chat.id, message.id)
			# text = f'<b>{message.from_user.first_name}</b>, вам не разрешено использовать команду <b>/raw_command</b>'
			# try:
				# bot.send_message(message.chat.id, text, parse_mode='html')
			# except Exception:
				# log(f'Ошибка отправки сообщения, /raw_command не разрешен', message.chat.id)
		# else:																					# Если разрешена блокировка других участников группы или основатель группы
			# log(f'{member_info(message.from_user)} отправил запрос {message.text}', message.chat.id, message.id)
			# try:
				# raw_command = message.text.split(' ', 1)[1]
				# if raw_command.startswith == 'bot.'
					# print(raw_command)
					# print(exec(raw_command))			# Здесь ДЫРА в безопасности
					# #bot.send_message(message.chat.id, text, parse_mode='html')
			# except Exception:
				# log(f'Ошибка выполнения /raw_command', message.chat.id)

# ======================================================================


# =============================== /cens ================================

@bot.message_handler(commands=['cens'])											# Выполняется, если сообщение содержит команду /cens
def handler_cens(message):
	global censured_list
	if is_group_allowed(message, 'handler_cens'):
		if message.from_user.id != message.chat.id:
			text = f"Команда /cens не работает в группе.\bОткройте чат с ботом и отправьте команду <b>/cens</b>"
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки ответа на /cens в группе от {member_info(message.from_user)}', message.chat.id, message.id)
		else:
			for item in censured_list[::-1]:
				if item['user_id'] == message.from_user.id:
					text_message = item['message']
					try:
						bot.send_message(message.chat.id, text_message, parse_mode='html')
					except Exception:
						log(f'Ошибка отправки текста на /cens от {member_info(message.from_user)}', message.chat.id, message.id)
					else: censured_list.remove(item)
			if not 'text_message' in locals():
				text = f"Отсутствуют записи об удалённых сообщениях с ругательствами"
				try:
					bot.send_message(message.chat.id, text, parse_mode='html')
				except Exception:
					log(f'Ошибка отправки пустого ответа на /cens от {member_info(message.from_user)}', message.chat.id, message.id)

# ======================================================================


# ============================= /get_log ===============================

@bot.message_handler(commands=['get_log'])										# Выполняется, если сообщение содержит команду /get_log
def handler_get_log(message):
	if (message.from_user.id in config.admins_id) and (message.from_user.id == message.chat.id): # Запрос от доверенных и лично боту

		log(f'Команда /get_log от {member_info(message.from_user)}', message.chat.id, message.id)

		if len(message.text.split()) > 1:											# Если передано количество строк вместе с командой /get_log
			try:
				length = int(message.text.split()[1])								# Количество строк из таблицы log, которое было запрошено
			except Exception:
				length = None
				log(f'Ошибка получения количества строк из запроса /get_log', message.chat.id, message.id)

			if len(message.text.split()) > 2:										# Если переданы количество строк и маркер
				marker = ' '.join(message.text.split()[2:])
			else:
				marker = ''

			if length:
				table_name = 'log'
				sqlite_query = f"SELECT chat_id, message_id, log_text, unix_time FROM {table_name} ORDER BY id DESC"
				with sqlite3.connect(path_db) as sqlite_connection:
					cursor = sqlite_connection.cursor()
					cursor.execute(sqlite_query)
					records = cursor.fetchall()										# Необработанный список из таблицы log нужен чтобы после получить количество записей по маркеру
					
				log_text = ''
				j = 0
				for record in records:
					if marker.casefold() in record[2].casefold():
						j += 1
						
						if record[0]: chat_id = f' {record[0]}'
						else: chat_id = ''
						
						if record[1]: message_id = f' {record[1]}'
						else: message_id = ''
						
						log_text += f'\n\n {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(record[3]))} {chat_id} {message_id} {record[2]}'
						if j == length: break

				try:
					bot.send_message(message.chat.id, log_text, parse_mode='html') # Отправка строк log
				except Exception:
					log(f'Ошибка отправки {length} строк log в ответ на /get_log', message.chat.id, message.id)		

		else:																					# Отправить файл log, если НЕ передано количество строк вместе с командой /get_log
			upload_filename = f'log_{time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())}.txt'
			with open(path_log, "rb") as file:
				try:
					bot.send_document(message.chat.id, document=file, visible_file_name=upload_filename)
				except Exception:
					log(f'Ошибка отправки файла log в ответ на /get_log', message.chat.id, message.id)

# ======================================================================


# =========================== /get_chat_id =============================
# ---------------------- Вывод id чата  отладки ------------------------

@bot.message_handler(commands=['get_chat_id'])									# Выполняется, если сообщение содержит команду /get_chat_id
def handler_get_chat_id(message):
	messages_add_new(message)															# Запись в таблицу message
	log(f'Команда /get_chat_id от {member_info(message.from_user)}', message.chat.id, message.id)
	text = f'{message.chat.id}'
	try:
		bot.send_message(message.chat.id, text, parse_mode='html')			# Отправка сообщения в чат
	except Exception:
		log(f'Ошибка отправки chat_id в ответ на /get_chat_id', message.chat.id, message.id)

# ======================================================================


# ============================ /get_stat ===============================
# ------------------------- Вывод статистики ---------------------------

@bot.message_handler(commands=['get_stat', 'statistics'])										# Выполняется, если сообщение содержит команду /get_stat
def handler_get_stat(message):
	if is_group_allowed(message):	# Проверка группы
		messages_add_new(message)														# Запись в таблицу message

		if len(message.text.split()) > 1:											# С командой передан аргумент
			try:
				period = int(message.text.split()[1])
			except Exception:
				log(f'Ошибка получения периода из команды {message.text}', message.chat.id, message.id)
			else:
				log(f'Команда /get_stat {period} от {member_info(message.from_user)}', message.chat.id, message.id)
				statistics_send(message.chat.id, period)

		else:
			log(f'Команда /get_stat от {member_info(message.from_user)}', message.chat.id, message.id)
			statistics_send(message.chat.id)

# ======================================================================


# ============================== /test =================================
# ---------------- Вывод данных в терминал для отладки -----------------

@bot.message_handler(commands=['test'])									# Выполняется, если сообщение содержит команду /test или /tst
def handler_test(message):
	if is_group_allowed(message):	# Проверка группы
		messages_add_new(message)														# Запись в таблицу message

		log(f'Команда {message.text} от {member_info(message.from_user)}', message.chat.id, message.id)

		limit = 4096	# Максимальная длина сообщения
		if len(str(message)) > limit:
			for x in range(0, len(str(message)), limit):
				try:
					bot.send_message(message.chat.id, str(message)[x:x+limit])# Отправка части raw сообщения в чат
				except Exception:
					log(f'Ошибка отправки части [{x}:{x+limit}] сообщения в ответ на /test', message.chat.id, message.id)
		else:
			try:
				bot.send_message(message.chat.id, message)						# Отправка raw сообщения в чат
			except Exception:
				log(f'Ошибка отправки сообщения в ответ на /test', message.chat.id, message.id)

		print('\n\nmessage')
		print(message)

		try:
			member_raw_data = bot.get_chat_member(message.chat.id, message.from_user.id)	# Получение данных участника
			bot.send_message(message.chat.id, member_raw_data)					# Отправка raw данных участника в чат
		except Exception:
			log(f'Ошибка отправки данных пользователя в ответ на /test', message.chat.id, message.id)
		else:
			print('\n\nget_chat_member')
			print(member_raw_data)

		if message.reply_to_message:
			try:
				member_raw_data = bot.get_chat_member(message.chat.id, message.reply_to_message.from_user.id)	# Получение данных участника
				bot.send_message(message.chat.id, member_raw_data)				# Отправка raw данных участника в чат
			except Exception:
				log(f'Ошибка отправки данных пользователя reply_to_message в ответ на /test', message.chat.id, message.id)
			else:
				print('\n\nget_chat_member reply_to_message')
				print(member_raw_data)

# ======================================================================


# ============================ /member_id ==============================
# --------------- Вывод информации о пользователях по id ---------------

@bot.message_handler(commands=['member_id'])
def handler_member_id(message):
	if is_group_allowed(message):														# Проверка группы
		messages_add_new(message)														# Запись в таблицу message
		log(f'Команда {message.text} от {member_info(message.from_user)}', message.chat.id, message.id)
		
		count = 0
		if len(message.text.split(' ')) > 1:
			ids = message.text.split(' ')[1:]
			for id in ids:
				if id.isnumeric():
					count += 1
					try:			
						member_raw_data = bot.get_chat_member(message.chat.id, id)	# Получение данных участника
						bot.send_message(message.chat.id, member_raw_data)		# Отправка raw данных участника в чат по id
					except Exception:
						log(f'Ошибка получения данных пользователя {id}', message.chat.id, message.id)

		if count == 0:
			text = f'С командой <b>/member_id</b> не передан <b>id</b>'
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения, не передан id с командой /member_id', message.chat.id, message.id)
			
# ======================================================================


# ============================== /help =================================
# --------------------------- Вывод ссылок -----------------------------

@bot.message_handler(regexp=r'(?i)\A((\/|@|h)h(e?)lp|(\/|@|s)st(a?)rt|(\/|@|i)inf(o|))\b')# Выполняется, если начало сообщения содержит команды
def handler_help(message):
	if is_group_allowed(message, 'handler_help'):								# Проверка группы
		messages_add_new(message)														# Запись в таблицу message

		log(f'Команда /help от {member_info(message.from_user)}', message.chat.id, message.id)

		inline_buttons = telebot.types.InlineKeyboardMarkup()					# Создаём кнопки
		for rows in config.help_links:
			row_buttons = []
			for site in rows:
				if site[0] and 'http' in site[1]:
					row_buttons.append(telebot.types.InlineKeyboardButton(site[0], url=site[1])) # Добавляем в список кнопку
			inline_buttons.keyboard.append(row_buttons)							# Формируем строку кнопок из списка 

		text = (
			f"Чтобы заблокировать негодяя, ответьте на его сообщение"
			f" текстом <b>@ban</b>, <b>/ban</b> или <b>bban</b>")
		try:																					
			bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=inline_buttons)
		except Exception:
			log(f'Ошибка отправки сообщения в ответ на /help {message.id}', message.chat.id, message.id)

# ======================================================================


# ====================== Удаление аудио сообщений ======================

@bot.message_handler(func=lambda message: True, content_types=['audio', 'voice'])
def handler_audio_messages(message):
	if is_group_allowed(message):	# Проверка группы
		messages_add_new(message)														# Запись в таблицу message

		if config.delete_audio_message:
			try:
				bot.delete_message(message.chat.id, message.id)						# Удалить голосовое сообщение
			except Exception:
				log(f'Ошибка удаления аудио сообщения {message.id}', message.chat.id, message.id)
			else:
				log(f'Удалено аудио сообщение {message.id} от {member_info(message.from_user)}', message.chat.id, message.id)

# ======================================================================


# ============================== @ban ==================================
# -------------- Голосование блокировки участника группы ---------------

@bot.message_handler(regexp=r'(?i)\A(\/|@|b)ban\b')
def handler_ban(message):
	if is_group_allowed(message):														# Проверка группы
		messages_add_new(message)														# Запись в таблицу message
		checkin_voted, time_joined_voted = member_checkin(message.chat.id, message.from_user.id)
		text = ''
		
		if (checkin_voted == False):	# Участник прошёл проверку
			log(f'Запрос ban от {member_info(message.from_user)} не прошедшего проверку', message.chat.id, message.id)
		
		count = 1
		# Если участник, применяющий ban, состоит в группе менее nnn дней
		member_voted_time_in_group = time.time()-time_joined_voted
		if member_voted_time_in_group < (config.days_in_group_to_use_ban*24*60*60):
			text = f'{count}. Вам запрещено использовать команду /ban, так как Вы состоите в группе меньше {config.days_in_group_to_use_ban} дней.\n'
			log(f'Запрос ban от {member_info(message.from_user)} в группе менее {config.days_in_group_to_use_ban} дней ({int((time.time()-time_joined_voted)/(24*60*60))})', message.chat.id, message.id)
			count += 1

		# Если ban отправлен НЕ ответом на другое сообщение
		if not message.reply_to_message:												
			log(f'Запрос ban не в ответ от {member_info(message.from_user)}', message.chat.id, message.id)
			text = f'{text}{count}. Команду <b>@ban</b>, <b>/ban</b> или <b>bban</b> необходимо отправить в ответ на сообщение участника группы, которого предлагается заблокировать.\n'
			count += 1

		# Если ban пытаются применить к участнику, который давно присоединился к группе
		if message.reply_to_message:
			_, time_joined_banned = member_checkin(message.chat.id, message.reply_to_message.from_user.id)
			member_banned_time_in_group = time.time() - time_joined_banned
			if member_banned_time_in_group > (config.days_in_group_can_be_banned*24*60*60):
				log(f'Запрос ban от {member_info(message.from_user)} на участника {member_info(message.reply_to_message.from_user)}, который более недели', message.chat.id, message.id)
				text = f'{text}{count}. <b>/ban</b> может быть применён только к участнику, состоящему в группе менее недели. Появится админ и всех рассудит.\n'
				for admin_id in config.admins_id:
					try:
						admin_username = bot.get_chat_member(message.chat.id, admin_id).user.username
					except Exception:
						log(f'Ошибка получения username админа {admin_id}', message.chat.id)
					else:
						text += f'@{admin_username} '

		if text:
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения ban', message.chat.id)

		else:																					# Если ban разрешён
			banned_user_id = message.reply_to_message.from_user.id			# id пользователя для блокировки
			banned_user_first_name = str(message.reply_to_message.from_user.first_name)
			
			log(f'Запрос ban от {member_info(message.from_user)} на блокировку {member_info(message.reply_to_message.from_user)}', message.chat.id, message.id)

			inline_button = telebot.types.InlineKeyboardMarkup()				# Кнопка Забанить
			inline_button.add(telebot.types.InlineKeyboardButton(f'Забанить 1/{config.members_poll_for_ban}', callback_data=f'ban|||{banned_user_id}|||{banned_user_first_name}|||{message.id}|||{message.date}'))

			text = f'Появилось предложение забанить:\n<b>{banned_user_first_name}</b>'
			try:
				bot.send_message(message.chat.id, text, parse_mode='html', reply_markup=inline_button)
			except Exception:
				log(f'Ошибка отправки кнопки Забанить', message.chat.id)
			else:
				ban_vote_add(message.chat.id, banned_user_id, user_voted_id=message.from_user.id) # только голосование за ban

# ======================================================================


# =========================== /ban_id /unban_id ========================

@bot.message_handler(commands=['ban_id', 'unban_id'])							# Выполняется, если сообщение содержит команду /ban_id или /unban_id
def handler_ban_id(message):
	command = message.text.split()[0] # Содержит ban_id или unban_id
	log(f'{member_info(message.from_user)} отправил команду {message.text}', message.chat.id, message.id)
	
	if not is_admin(message.chat.id, message.from_user.id):
		log(f'Команда {command} не от администратора группы {member_info(message.from_user)}', message.chat.id, message.id)
		text = f'<b>{message.from_user.first_name}</b>, вам не разрешено использовать команду <b>{command}</b>'
		try:
			bot.send_message(message.chat.id, text, parse_mode='html')
		except Exception:
			log(f'Ошибка отправки сообщения, {command} не разрешен', message.chat.id)
	else:																					# Если разрешена блокировка других участников группы или основатель группы
		ids_to_block = message.text.split(' ')[1:]	# Список id, переданных с командой /(un)ban_id
		if len(ids_to_block) == 0:
			text = f'С командой {command} не переданы id'
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения, c {command} не переданы id', message.chat.id)
		else:
			count = 0
			for id in ids_to_block:
				if id.isnumeric():
					if command == '/ban_id':
						block_member(message.chat.id, id)			# ban_id
					elif command == '/unban_id':
						block_member(message.chat.id, id, period_block=60)	# unban_id
					count += 1
				if count < len(ids_to_block):
					time.sleep(3)

			try:
				bot.send_message(message.chat.id, f'Завершено {count}/{len(ids_to_block)}', parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения о завершении {command}', message.chat.id)

# ======================================================================


# =============================== @mute ================================
# -------------- Временная блокировка участника группы -----------------

@bot.message_handler(regexp=r'(?i)\A(\/|@|m)mute\b')
def handler_mute(message):
	if is_group_allowed(message):														# Проверка группы
		messages_add_new(message)														# Запись в таблицу message
		text = ''
		
		count = 1
		check_rights = is_admin(message.chat.id, message.from_user.id)
		if check_rights == False:
			text = f'{count}. <b>{message.from_user.first_name}</b>, вам не разрешено использовать команду <b>/mute</b>.\n'
			count += 1
		if check_rights == None:
			text = f'{count}. <b>{message.from_user.first_name}</b>, не удалось проверить права.\n'
			count += 1
	
		if not message.reply_to_message:	# Если mute отправлен НЕ ответом на другое сообщение
			log(f'Запрос mute не в ответ от {member_info(message.from_user)}', message.chat.id, message.id)
			text = (
				f'{text}{count}. Отправьте <b>/mute</b> в ответ на сообщение пользователя, '
				f'которого необходимо заблокировать.'
				f'\nУкажите количество часов блокировки (по умолчанию 24). '
				f'Например, <b>/mute 12</b>.')

		if text:
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения mute', message.chat.id)

		else:		# Mute разрешён
			log(f'{member_info(message.from_user)} отправил запрос {message.id} на участника {member_info(message.reply_to_message.from_user)}: {message.text}', message.chat.id, message.id)

			line = message.text.split()
			try:
				time_mute_h = int(line[1])												# Получение время часов mute из текста
			except Exception:
				time_mute_h = 24															# Время mute 24 часа по умолчанию
			
			time_mute_s = time.time() + time_mute_h * 60 * 60			# Расчёт времени окончания блокировки
			#time_mute_s = time.time() + 60										# для тестов
			try:
				check_mute = bot.restrict_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, until_date=time_mute_s)
			except Exception:
				log(f'Ошибка выполнения mute пользователя {member_info(message.reply_to_message.from_user)}', message.chat.id, message.id)
			else:
				if check_mute:
					log(f'mute на {time_mute_h} ч. участника {member_info(message.reply_to_message.from_user)}', message.chat.id, message.id)
					text = (
						f'<b>{message.reply_to_message.from_user.first_name}</b>,'
						f'самое время отвлечься на что-нибудь другое.'
						f'\nБлокировка действует в течении {time_mute_h} ч.')
					try:
						bot.send_message(message.chat.id, text, parse_mode='html')
					except Exception:
						log(f'Ошибка отправки уведомления mute', message.chat.id, message.id)

# ======================================================================


# ============================== unmute ================================
# --------------- Снятие блокировки с участника группы -----------------

@bot.message_handler(regexp=r'(?i)\A(\/|@|)(un|u)mute\b')
def handler_unmute(message):
	if is_group_allowed(message):														# Проверка группы
		messages_add_new(message)														# Запись в таблицу message			
		text = ''

		check_rights = is_admin(message.chat.id, message.from_user.id)
		if check_rights == False:
			text = f'<b>{message.from_user.first_name}</b>, вам не разрешено использовать команду <b>unmute</b>.\n'
		if check_rights == None:
			text = f'<b>{message.from_user.first_name}</b>, не удалось проверить права.\n'

		if not message.reply_to_message:
			log(f'Запрос unmute не в ответ от {member_info(message.from_user)}', message.chat.id, message.id)
			text = (
				f'{text}Отправьте <b>unmute</b> или <b>umute</b>'
				f' в ответ на сообщение пользователя, '
				f'с которого необходимо снять временную блокировку.')

		if text:
			try:
				bot.send_message(message.chat.id, text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки сообщения unmute', message.chat.id, message.id)

		else:		# Если разрешено использовать unmute
			log(f'{member_info(message.from_user)} отправил запрос {message.id} на участника {member_info(message.reply_to_message.from_user)}: {message.text}', message.chat.id, message.id)

			try:
				check_unmute = bot.restrict_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, can_send_messages = True)
			except Exception:
				log(f'Ошибка при unmute участника {member_info(message.reply_to_message.from_user)}', message.chat.id, message.id)
			else:
				if check_unmute:
					log(f'unmute участника {member_info(message.reply_to_message.from_user)}', message.chat.id, message.id)
					text = f'<b>{message.reply_to_message.from_user.first_name}</b>, блокировка снята.'
					try:
						bot.send_message(message.chat.id, text, parse_mode='html')
					except Exception:
						log(f'Ошибка отправки уведомления unmute', message.chat.id, message.id)

# ======================================================================


# ======================= Новый участник группы ========================

@bot.message_handler(content_types=["new_chat_members"])						# Если обнаружено подключение к группе нового участника
def handler_new_chat_members(message):
	if is_group_allowed(message):														# Проверка группы
		if message.from_user.id != message.new_chat_members[0].id:			# Не выполнять проверку, если нового участника кто-то присоединил к группе
			for new_member in message.new_chat_members:							# При подключении участников, это массив
				log(f'Нового участника {member_info(new_member)} присоединил {member_info(message.from_user)}', message.chat.id, message.id)

				member_add_new(message.chat.id, new_member.id, message.date)# Записать данные нового участника подключенного кем-то
				member_set_checked(message.chat.id, new_member.id)				# Подтвердить проверку нового участника

		else: # Новый участник подключился самостоятельно
			new_member = {'chat_id': message.chat.id, 'user_id': message.from_user.id, 'checked': 0}
			global new_members_list
			new_members_list.append(new_member)

			log(f'Новый участник {member_info(message.from_user)}', message.chat.id, message.id)

			if message.from_user.username:
				username = f' (@{message.from_user.username})'
			else: username = ''
			text = (
				f'<b>{message.from_user.first_name}</b>{username},'
				f' с целью защиты от спама необходимо пройти проверку. '
				f'{config.checkin_text}'
				f'\n\nЧерез {config.minutes_for_checkin} минуты Вы будете исключены из группы. '
				f'Повторная попытка будет возможна через {config.minutes_between_checkin} минут.'
				f'\n\nНеобходимую информацию можно найти в описании группы '
				f'или отправив команду /help'
				f'\nДля проверки по изображению отправьте команду /captcha')
			try:
				invite_message = bot.send_message(message.chat.id, text, parse_mode='html') # Отправка приветствия нового участника группы
			except Exception:
				invite_message = None
				log(f'Ошибка отправки сообщения проверки нового участника', message.chat.id)
			
			member_add_new(message.chat.id, message.new_chat_members[0].id, message.date)	# Заносим данные о новом пользователя, как можно раньше

			# Периодический опрос, не прошёл ли новый участник проверку через содержимое списка new_members_list
			time_check_end = time.monotonic() + config.minutes_for_checkin * 60
			while time.monotonic() < time_check_end:
				# Если новый участник удалён за спам или прошёл проверку 
				if (new_member not in new_members_list) or (new_member['checked'] == 1): 
					break
				else: time.sleep(1)

			# Новый участник прошёл проверку
			if	(new_member in new_members_list) and (new_member['checked'] == 1):
				member_set_checked(message.chat.id, message.from_user.id)
				new_members_list.remove(new_member)
				if message.from_user.username:
					username = f' (@{message.from_user.username})'
				else: username = ''
				text = (
					f'<b>{message.from_user.first_name}</b>{username}'
					f', проверка пройдена. '
					f'Добро пожаловать в группу <b>{message.chat.title}</b>.'
					f' Правила простые, в любой ситуации оставаться <b>Человеком</b>.'
					f' Для получения дополнительной информации отправьте команду /help')
				try:
					bot.send_message(message.chat.id, text, parse_mode='html') # Отправка сообщения подтверждения проверки
				except Exception:
					log(f'Ошибка отправки сообщения об успешной проверке нового участника', message.chat.id)
				else:
					log(f'Новый участник {member_info(message.from_user)} прошёл проверку', message.chat.id)

			# Новый участник НЕ прошёл проверку
			if (new_member in new_members_list) and (new_member['checked'] == 0):
				try:
					bot.delete_message(message.chat.id, message.id)				# Удалить уведомление о подключении к группе нового участника
				except Exception:
					log(f'Ошибка удаления уведомления {message.id} о подключении к группе нового участника {message.from_user.id}', message.chat.id, message.id)

				new_members_list.remove(new_member)

				mfcc = member_false_checkin_count(message.chat.id, message.from_user.id, config.period_allowed_checks)
				mfcca = member_false_checkin_count(message.chat.id, message.from_user.id)
				if mfcc > 1:
					log(f'Новый участник {member_info(message.from_user)} не прошёл проверку {mfcc} раз(а) за {config.period_allowed_checks} дней', message.chat.id)
				else:
					log(f'Новый участник {member_info(message.from_user)} не прошёл проверку', message.chat.id)
				if mfcca > 1:
					log(f'Новый участник {member_info(message.from_user)} всего пытался пройти проверку {mfcca} раз')

				if mfcc >= config.number_allowed_checks:
					block_member(message.chat.id, message.from_user.id)	# Блокировать участника навсегда при множественных неудачных проверках
				else:
					block_member(message.chat.id, message.from_user.id, period_block=config.minutes_between_checkin*60)	# Блокировать участника временно при неудачной проверке

			captcha_del_records(message.chat.id, message.from_user.id)		# Удаление последней captcha

			try:
				bot.delete_message(message.chat.id, invite_message.id)		# Удалить приветствие нового участника
			except Exception:
				log(f'Ошибка удаления приветствия нового участника {invite_message.id}', message.chat.id, invite_message.id)

# ======================================================================


# ============================== /captcha ==============================

@bot.message_handler(commands=['captcha'])										# Выполняется, если сообщение содержит команду /captcha
def handler_captcha(message):
	global captcha_list
	global new_members_list
	
	if is_group_allowed(message):	# Проверка группы
		
		if not {'chat_id': message.chat.id, 'user_id': message.from_user.id, 'checked': 0} in new_members_list:
			log(f'Запрос captcha не от нового пользователя {member_info(message.from_user)}', message.chat.id, message.id)

		else:
			try:																				# Удаление сообщения с командой /captcha
				bot.delete_message(message.chat.id, message.id)					
				#log(f'Удалено сообщение /captcha id {message.id} от нового участника {member_info(message.from_user)}', message.chat.id, message.id)
			except Exception:
				log(f'Ошибка удаления сообщения /captcha {message.id} от нового участника {member_info(message.from_user)}', message.chat.id, message.id)

			captcha_del_records(message.chat.id, message.from_user.id)		# Удаление предыдущей captcha
				
			captcha_size_num = 2															# Captcha image size number (2 -> 640x360)
			generator = CaptchaGenerator(captcha_size_num)						# Create Captcha Generator object of specified size
			captcha = generator.gen_captcha_image(difficult_level=3)			# Generate a captcha image
			catcha_image = captcha.image												# Get information of standard captcha
			captcha_characters = captcha.characters								# Цифры из captcha
			
			text = (
				f'Отправьте сообщение с цифрами из изображения.'
				f'\nДля отправки другого изображения повторно используйте команду /captcha')
			try:
				message_captcha = bot.send_photo(message.chat.id, photo=catcha_image, caption=text, parse_mode='html')
			except Exception:
				log(f'Ошибка отправки captcha для {member_info(message.from_user)}', message.chat.id)
			else:
				captcha_list.append({'chat_id': message.chat.id, 'user_id': message.from_user.id, 'captcha': captcha_characters, 'captcha_id': message_captcha.id})
				log(f'Отправлена captcha {captcha_characters} с id {message_captcha.id} для {member_info(message.from_user)}', message.chat.id, message_captcha.id)

# ======================================================================


# =========================== Обработка сообщений ======================

@bot.message_handler(func=lambda message: True, content_types=['photo', 'video', 'document', 'text', 'location', 'contact', 'sticker'])
def handler_messages(message):
	if is_group_allowed(message):														# Проверка группы
		messages_add_new(message)														# Запись в таблицу message

# ----------------- Проверка нового участника группы -------------------

		global new_members_list
		for new_member in new_members_list: # Поиск в списке новых участников
			if ((new_member['chat_id'] == message.chat.id)
			and (new_member['user_id'] == message.from_user.id)
			and (new_member['checked'] == 0)):
				is_new_member = True
				break
		else: is_new_member = False

		if is_new_member:	# Если участник проходит проверку
			try:
				bot.delete_message(message.chat.id, message.id)					# Удалить сообщение нового участника группы
			except Exception:
				log(f'Ошибка удаления сообщения {message.id} {member_info(message.from_user)}', message.chat.id, message.id)
			else:
				log(f'Удалено сообщение {message.id} нового участника {member_info(message.from_user)}: {message.text}', message.chat.id, message.id)

			# Проверка нового участника на спам
			for spam_marker in spam_set_new_member:
				if (len(message.text.split(' ')) > 20
				and (spam_marker in str(message.text).casefold() or spam_marker in str(message.caption).casefold())):
					new_members_list.remove(new_member)
					log(f'Спам метка -{spam_marker}- от нового участника {member_info(message.from_user)}', message.chat.id, message.id)
					block_member(message.chat.id, message.from_user.id)		# Блокировка нового участника за спам
					break
			else:
				for captcha_record in captcha_list[::-1]:							# Проверка каптчи
					if ((captcha_record['chat_id'] == message.chat.id)
					and (captcha_record['user_id'] == message.from_user.id)
					and (str(captcha_record['captcha']) in str(message.text).casefold()[:20])):
						new_member['checked'] = 1
						break
				else:
					for marker in config.check_marker:								# Перебор ключевых фраз
						if marker.casefold() in str(message.text).casefold()[:20]:
							new_member['checked'] = 1
							break

		else:		# Если участник НЕ проходит проверку

# -------------- Фильтр спама с блокировкой участника ------------------

			for spam_marker in spam_set:
				if (spam_marker in str(message.text).casefold()
				or spam_marker in str(message.caption).casefold()
				or spam_marker in str(message.from_user.first_name).casefold()):
					messages_delete(message.chat.id, message.from_user.id)
					log(f'Спам метка -{spam_marker}- от {member_info(message.from_user)}', message.chat.id, message.id)
					block_member(message.chat.id, message.from_user.id)	# Блокировка участника за спам
					break

			else:				# Если пройдена проверка на спам 

# ------------------------ Фильтр ругательств --------------------------

				words_for_check = set()
				if message.text:
					words_for_check = words_for_check | {i.lower().translate(str.maketrans('', '', string.punctuation)) for i in message.text.split()}
				if message.caption:
					words_for_check = words_for_check | {i.lower().translate(str.maketrans('', '', string.punctuation)) for i in message.caption.split()}

				censure_check = words_for_check.intersection(censure_set)
				if censure_check:
					global censured_list
					censured_list.append({'chat_id': message.chat.id, 'user_id': message.from_user.id, 'message': message.text})
					#print(censured_list)
					log_text = f"Ругательство -{' '.join(censure_check)}- от {member_info(message.from_user)}"
					log(log_text, message.chat.id, message.id)

					if message.from_user.username:
						username = f' (@{message.from_user.username})'
					else: username = ''
					text = (
						f'<b>{message.from_user.first_name}</b>{username}'
						f', пожалуйста, не ругайтесь.'
						f'\nДля получения текста Вашего сообщения, откройте чат с ботом и отправьте команду <b>/cens</b>')
					try:
						bot.reply_to(message, text, parse_mode='html', disable_web_page_preview=True)
					except Exception:
						log(f'Ошибка отправки уведомления о ругательстве {member_info(message.from_user)}', message.chat.id)
						
					try:
						bot.delete_message(message.chat.id, message.id)				# Удалить ругательное сообщение
					except Exception:
						log(f'Ошибка удаления ругательного сообщения', message.chat.id, message.id)

# ------- Фильтр для удаления сообщений без блокировки участника -------

				for pattern in config.markers_to_delete:
					if pattern:
						marker_find_text = re.search(pattern, str(message.text).casefold())
						marker_find_caption = re.search(pattern, str(message.caption).casefold())

						marker = False
						if marker_find_text:
							marker =  marker_find_text.group(0)
						if marker_find_caption:
							marker =  marker_find_caption.group(0)

						if marker:
							log(f'Упоминание -{marker}- от {member_info(message.from_user)}', message.chat.id, message.id)
							try:
								bot.delete_message(message.chat.id, message.id)
							except Exception:
								log(f'Ошибка удаления сообщения {message.id} с меткой -{marker}-', message.chat.id, message.id)
							break

# ----------------------- Безымянные участники -------------------------

				else:
					if (not re.search(r'[0-9А-Яа-яA-Za-z]', str(message.from_user.first_name))
					and (log_marker_last_id(message.chat.id, 'Сообщение участника без имени') < message.id - config.can_repeat_info)):
						log(f'Сообщение участника без имени {message.from_user.id}', message.chat.id, message.id)
						try:
							#bot.delete_message(message.chat.id, message.id)				# Удаление сообщения безымянного участника
							text = f'Участник группы с id <b>{message.from_user.id}</b>, пожалуйста, добавьте к имени Вашего профиля символы латиницы, кирилицы или цифры. Спасибо.'
							bot.reply_to(message, text, parse_mode='html') 					# Отправка сообщения
						except Exception:
							log(f'Ошибка удаления сообщения от безымянного участника', message.chat.id, message.id)
							
# -------------------------- Сообщение боту ----------------------------

					if message.reply_to_message:
						if (str(message.reply_to_message.from_user.id) == config.bot_id
						and ((log_marker_last_id(message.chat.id, 'Попытка поговорить с ботом') < message.id - config.can_repeat_info))):
							log(f'Попытка поговорить с ботом участника {member_info(message.from_user)}', message.chat.id, message.id)
							text = f'Я бот, буду рад с Вами пообщаться после того, как мне приделают искусственный интеллект.'
							try:
								bot.reply_to(message, text, parse_mode='html', disable_web_page_preview=True)
							except Exception:
								log(f'Ошибка отправки сообщения о попытке поговорить с ботом {member_info(message.from_user)}', message.chat.id)

# --------------- Фильтр здоровенных ссылок aliexpress -----------------

					#if re.search(r'https://aliexpress(.*?)(sku_id=|spm=|af=)', str(message.text).casefold()) \
					#or re.search(r'https://aliexpress(.*?)(sku_id=|spm=|af=)', str(message.caption).casefold()):
					if (re.search(r'https://(www\.)?aliexpress\.(ru|com)/item/(\d*)\.html\?', str(message.text).casefold())
					or re.search(r'https://(www\.)?aliexpress\.(ru|com)/item/(\d*)\.html\?', str(message.caption).casefold())):
						log(f'Сообщение {message.id} со здоровенной ссылкой aliexpress от {member_info(message.from_user)}', message.chat.id, message.id)
						
						pattern = r'html\?(.*?)(\s|\n|$)'
						new_message = re.sub(pattern, f'html\n', message.text)
						if message.from_user.username:
							username = f' (@{message.from_user.username})'
						else:
							username = ''
						
						text = f'<b>{message.from_user.first_name}</b>{username},'\
								 f' Ваше сообщение заменено'\
								 f'\n{new_message}'
						try:
							check_send = bot.send_message(message.chat.id, text, disable_web_page_preview=True, parse_mode='html')# Отправка сообщения с короткой ссылкой aliexpress
						except Exception:
							log(f'Ошибка отправки сообщения с изменённой ссылкой aliexpress', message.chat.id)
						else:
							if check_send:
								try:
									bot.delete_message(message.chat.id, message.id)				# Удалить сообщение aliexpress
								except Exception:
									log(f'Ошибка удаления сообщения aliexpress {message.id}', message.chat.id, message.id)

# ---------------- Отправка ссылок по ключевым фразам ------------------
					
					for marker in config.markers_links:
						if marker:
							pattern = marker[0]
							url = marker[1]
							marker_find_in_text = re.search(pattern, str(message.text).casefold())
							marker_find_in_caption = re.search(pattern, str(message.caption).casefold())

							if ((marker_find_in_text or marker_find_in_caption)
							and (url not in str(message.text).casefold())
							and (url not in str(message.caption).casefold())
							and ((log_marker_last_id(message.chat.id, f'Запрос {url}') < message.id - config.can_repeat_info))):
								log(f'Запрос {url} от {member_info(message.from_user)}', message.chat.id, message.id)
								text = marker[2]
								try:
									bot.send_message(message.chat.id, text, parse_mode='html', disable_web_page_preview=True)
								except Exception:
									log(f'Ошибка отправки сообщения по запросу {url}', message.chat.id, message.id)
							elif marker_find_in_text or marker_find_in_caption:
								counter = log_marker_last_id(message.chat.id, f'Запрос {url}') - message.id
								log(f'Пропущен запрос {url} ({counter}) от {member_info(message.from_user)}', message.chat.id, message.id)

# ----------------------- Обработка STL и STEP -------------------------

					if message.content_type == 'document' and message.document.file_size < config.model3d_max_size_preview:
						file_name = message.document.file_name						# Имя файла
						file_ext = file_name[file_name.rfind('.')+1:]			# Расширение файла
						
						if (re.search(r'\b(st(e?)p|stl)\b', file_ext.casefold())):

							if (file_ext.casefold() == 'stl'):
								global stl_last_id
								check_for_stl_warning = stl_last_id < (message.id - config.can_repeat_info)
								stl_last_id = message.id
								#log(f'Отправлена stl модель {file_name}', message.chat.id, message.id)
								if check_for_stl_warning:
									text = (
										f'Обмен техническими моделями в формате'
										f' <b>stl</b> является дурным тоном. '
										f'Пожалуйста, используйте формат <b>step</b>.')
									try:
										bot.send_message(message.chat.id, text, parse_mode='html') # Отправка ругани на stl
									except Exception:
										log(f'Ошибка отправки ругани на stl', message.chat.id)

							file_info = bot.get_file(message.document.file_id)
							downloaded_file = bot.download_file(file_info.file_path)		# Скачивание 3d модели
							# Переименовать на случай, если имя содержит не ASCII символы. Необходимо для minirender
							path_model3d = os.path.join(path_dir_models3d, f'{file_info.file_unique_id}.{file_ext}')
							with open(path_model3d, 'wb') as new_file:
								new_file.write(downloaded_file)									# Сохранение 3d модели
							
							path_stl = re.sub(r'(?i)\.st(e?)p$', '.stl', path_model3d)
							
							if (re.search(r'\b(st(e?)p)\b', file_ext.casefold())):		# Если модель в формате STEP
								#log(f'Отправлена step модель {file_name}', message.chat.id, message.id)
								command = f'gmsh -v 0 "{path_model3d}" -0 -o "{path_stl}"'	# Конвертирование STEP в STL при помощи gmsh и occt
								os.system(command)
								os.remove(path_model3d)										# Удаление файла STEP

							if not os.path.exists(path_stl):
								log(f'Не найден файл {path_stl}', message.chat.id, message.id)
							else:
								if os.stat(path_stl).st_size < 100:
									log(f'Файл stl подозрительно маленький ({os.stat(path_stl).st_size} байт)', message.chat.id, message.id)
								else:
									command = f'{path_minirender} -o -- -tilt 30 -yaw 20 -w {config.preview_resolution} -h {config.preview_resolution} "{path_stl}" | convert - png:-'
									image = subprocess.check_output(command, shell=True)
									
									if sys.getsizeof(image) < 500:
										log(f'Ошибка создания превью файла -{file_name}-', message.chat.id, message.id)
									else:
										try:
											bot.send_document(message.chat.id, document=image, visible_file_name=f'{file_name[:file_name.rfind(".")]}.png') # Отправка как файла (более компактно)
											#bot.send_photo(message.chat.id, file, caption=image) # Отправка как фото
										except Exception:
											log(f'Ошибка отправки превью файла -{file_name}-', message.chat.id, message.id)
										else:
											log(f'Отправлено превью файла -{file_name}-', message.chat.id, message.id)
											# Удаление файлов STL и PNG
											os.remove(path_stl)

# ======================================================================


# ====================== Обработка запросов ban ========================

@bot.callback_query_handler(func=lambda call:True)
def handler_callback_query(call):
	if str(call.message.chat.id) in config.chats_id:
		checkin_voted, time_joined_voted = member_checkin(call.message.chat.id, call.from_user.id)

		# Участник прошёл проверку и состоит в группе больше 30 дней
		if (checkin_voted == False):	
			log(f'Голосование ban от {member_info(call.from_user)} не прошедшего проверку', call.message.chat.id, call.message.id)
		
		elif (time.time()-time_joined_voted < config.days_in_group_to_use_ban*24*60*60) and not is_admin(call.message.chat.id, call.from_user.id):
			log(f'Голосование ban от {member_info(call.from_user)} в группе менее {config.days_in_group_to_use_ban} дней ({(int(time.time())-time_joined_voted)/(24*60*60)})', call.message.chat.id, call.message.id)
		else:
			log(call.data, call.message.chat.id)

			# Запрос ban
			if call.data.split('|||')[0] == 'ban':									# Если запрос содержит ban
				banned_user_id = call.data.split('|||')[1]						# id пользователя для блокировки
				banned_first_name = call.data.split('|||')[2]					# Имя пользователя, которого блокируем
				banned_by_message_id = call.data.split('|||')[3]				# id сообщения, которое содержит ban 
				ban_init_time = call.data.split('|||')[4]							# Время создания опроса блокировки
				
				list_ban_voted = ban_voted_get_list(call.message.chat.id, banned_user_id, ban_init_time)	
				if call.from_user.id in list_ban_voted:							# Исключение дублирования голосования блокировки
				#if not True: # Если нужно временно разрешить дублировать запрос блокировки от одного пользователя
					log(f'Повторная попытка голосования за блокировку {banned_first_name} {banned_user_id} от {member_info(call.from_user)}', call.message.chat.id, call.message.id)
				else:
					log(f'{member_info(call.from_user)} cогласен заблокировать {banned_first_name} {banned_user_id}', call.message.chat.id, call.message.id)

					ban_vote_add(call.message.chat.id, banned_user_id, user_voted_id=call.from_user.id) # Добавление голоса за ban

					inline_button = telebot.types.InlineKeyboardMarkup()		# Изменённая кнопка Забанить
					inline_button.add(telebot.types.InlineKeyboardButton(f'Забанить {len(list_ban_voted)+1}/{config.members_poll_for_ban}', callback_data=f'ban|||{banned_user_id}|||{banned_first_name}|||{banned_by_message_id}|||{ban_init_time}'))

					new_text = f'Появилось предложение забанить:\n<b>{banned_first_name}</b>'
					try:
						bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text=new_text, parse_mode='html', reply_markup=inline_button)
					except Exception:
						log(f'Ошибка изменения голосования блокировки {call.message.id}', call.message.chat.id)

					if len(list_ban_voted)+1 >= config.members_poll_for_ban:	# Если достигнуто нужное число голосов за блокировку
						block_member(call.message.chat.id, banned_user_id)	# Блокировка участника после голосования
						messages_delete(call.message.chat.id, banned_user_id)	# Удаление сообщений заблокированного пользователя

						try:
							bot.delete_message(call.message.chat.id, call.message.id) # Удаление сообщения голосования блокировки
						except Exception:
							log(f'Ошибка удаления голосования блокировки {banned_user_id} {banned_first_name}', call.message.chat.id, call.message.id)

						try:
							bot.delete_message(call.message.chat.id, banned_by_message_id) # Удаление сообщения инициации блокировки
						except Exception:
							log(f'Ошибка удаления сообщения инициации блокировки {banned_user_id} {banned_first_name}', call.message.chat.id, banned_by_message_id)

# ======================================================================

if __name__ == '__main__':
	path_db = get_full_path(config.path_db)
	path_log = get_full_path(config.path_log)

	db_initialization()																	# Инициализация базы данных

	text = f'bot запущен на сервере '\
			 f'{os.uname().sysname} {os.uname().release}, '\
			 f'python {sys.version.split()[0]}, '\
			 f'pyTelegramBotAPI {telebot.version.__version__}'
	log(text)																				# Уведомление о запуке бота

	censure_set = set_from_file(get_full_path(config.path_censure))							# Множество материных слов
	spam_set = set_from_file(get_full_path(config.path_spam))									# Множество spam маркеров
	spam_set_new_member = set_from_file(get_full_path(config.path_spam_new_member))		# Множество spam маркеров при проверки новых участников

	stl_last_id = 0
	path_minirender = get_full_path(config.path_minirender)
	path_dir_models3d = get_full_path(config.path_models3d)
	if not os.path.exists(path_dir_models3d):
		os.makedirs(path_dir_models3d)

	captcha_list = []																		# Список действующих кодов captcha
	censured_list = []																	# Список сообщений с ругательствами
	new_members_list = []																# Список участников, проходящих проверку

	t1 = Thread(target=run_Bot)														# Поток 1 - Бот
	t2 = Thread(target=run_Schedulers)												# Поток 2 - Задачи по расписанию
	
	t1.start() 																				# Запуск потока 1
	t2.start()																				# Запуск потока 2
