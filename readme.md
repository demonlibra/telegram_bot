# Бот обсуживания группы Telegram

Разработка бота началась с просмотра видео  
[Гоша Дударь - Telegram Bot на Python / Создания ботов для начинающих за 30 минут](https://youtu.be/HodO2eBEz_8)  
[Школа itProger - Уроки Python для начинающих / Программирование на Питон с нуля ](https://www.youtube.com/playlist?list=PLDyJYA6aTY1lPWXBPk0gw6gR8fEtPDGKa)  
и прочтения книги **Простой Python. Современный стиль программирования** - *Билл Любанович*

Бот подходит для небольших групп со средней активностью  
Основан на [pyTelegramBotAPI](https://pypi.org/project/pyTelegramBotAPI) (режим **синхронный**, метод опроса [polling](https://docs-python.ru/packages/biblioteka-python-telegram-bot-python/ispolzovanie-webhook))  
Проверен на [Python 3.10.6](https://www.python.org) и [Ubuntu Server 22.04](https://ubuntu.com/download/server)  

Подробное описание функционала в файле [description.md](description.md) и на [форуме UNI](https://uni3d.store/viewtopic.php?t=1090)  

Для тестирования бот можно запустить даже на домашнем ноутбуке, статический и белый IP не требуются  
Для полноценного использования лучше использовать [VPS](https://ru.wikipedia.org/wiki/VPS)   
Бот подключен для тестов к Telegram группе [unitestgroup](https://t.me/unitestgroup)

## Установка

1. Установите **python3-pip** и **python3-venv**  
`sudo apt install python3-pip python3-venv`

2. Создайте и перейдите в каталог, например **bot**  
`mkdir bot`  
`cd bot`

3. Создайте и активируйте окружение **python_env**  
`python3 -m venv python_env`  
`source python_env/bin/activate`

4. Установите пакеты из списка **requirements.txt**  
`pip install -r requirements.txt`

5. Установите дополнительные библиотеки для работы модуля [multicolorcaptcha](https://pypi.org/project/multicolorcaptcha)  
`sudo apt install libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk`

6. Задайте параметры в файле **config.py**

7. Для создания миниатюр моделей **STL** используется [minirender](https://github.com/aslze/minirender).  
Установите **gmsh** для создания миниатюр моделей **STEP** через конвертирование в **STL**.  
`sudo apt install gmsh`  

## Запуск

1. Перейдите в каталог бота  
`cd bot`

2. Активируйте окружние и запустите сценарий **bot.py**  
`source python_env/bin/activate`  
`python3 bot.py` 

Для запуска сценария без активации окружения  
`python_env/bin/python3 bot.py`

## Запуск в качестве сервиса systemd

1. Создайте файл сервиса **bot.service**  
`nano /lib/systemd/system/bot.service`  

  
```
[Unit]
  Description=bot
 
[Service]
  WorkingDirectory=/home/<user_name>/bot
  ExecStart=/home/<user_name>/bot/python_env/bin/python3 /home/<user_name>/bot/bot.py
  Type=simple
  KillMode=process
 
  SyslogIdentifier=bot
  SyslogFacility=daemon
  StandardOutput=journal 
  
  Restart=on-failure
  RestartSec=10s
[Install]
  WantedBy=network-online.target
```  

Вместо **/home/<user_name>/bot/** задайте корректный путь к файлу сценария.

2. Обновите список сервисов **systemd** и запустите сервис **bot**  
`sudo systemctl daemon-reload`  
`sudo systemctl start bot`

Для проверки состояния сервиса выполните команду  
`sudo systemctl status bot`

Для автоматического запуска сервиса после перезагрузки системы выполните команду  
`sudo systemctl enable bot`

Для перезапуска сервиса выполните команду  
`sudo systemctl restart bot`

## Мониторинг

1. Мониторинг журнала **systemd**  
`journalctl -f -u bot`

2. Слежение за файлом **bot.log**  
`tail --follow bot/bot.log`