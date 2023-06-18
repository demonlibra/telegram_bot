# Бот обсуживания группы Telegram

Подробное описание функционала в файла [description.md](description.md) на [форуме UNI](https://uni3d.store/viewtopic.php?t=1090)  
Основан на [pyTelegramBotAPI](https://pypi.org/project/pyTelegramBotAPI)  
Проверен на [Python 3.10.6](https://www.python.org) и [Ubuntu Server 22.04](https://ubuntu.com/download/server)  

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
Вместо **/home/<user_name>/bot/** задайте корректный путь к файлу сценария.
  
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

2. Обновите список сервисов **systemd** и запустите сервис **bot**  
```
sudo systemctl daemon-reload
sudo systemctl start bot
sudo systemctl enable bot
```  
Для перезапуска сценария выполните команду  
`sudo systemctl restart bot`

## Мониторинг

1. Мониторинг журнала **systemd**  
`journalctl -f -u bot`

2. Слежение за файлом **bot.log**  
`tail --follow bot/bot.log`