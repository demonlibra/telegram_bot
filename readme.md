# Бот обсуживания группы Telegram

[Подробное описание функционала](https://uni3d.store/viewtopic.php?t=1090)  
Проверен с [Python 3.10.6](https://www.python.org)  
Основан на [pyTelegramBotAPI](https://pypi.org/project/pyTelegramBotAPI)

## Установка

1. Установите **python3-pip** и **python3-venv**  
`sudo apt install python3-pip python3-venv`

2. Создайте и перейдите в каталог, например **bot**  
```
mkdir bot  
cd bot
```

3. Создайте и активируйте окружение **python_env**  
`python3 -m venv python_env`  
`source python_env/bin/activate`

4. Установите пакеты из списка **requirements.txt**  
`pip install -r requirements.txt`

5. Установите дополнительные библиотеки для работы модуля [multicolorcaptcha](https://pypi.org/project/multicolorcaptcha)  
`sudo apt install libtiff5-dev libjpeg8-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python3-tk`

6. Проверьте параметры в файле **config.py**

7. Для создания миниатюр моделей **STL** используются [minirender](https://github.com/aslze/minirender)  
Установите **gmsh** для создания миниатюр моделей **STEP** через конвертирование в **STL**.  
`sudo apt install gmsh`  

## Запуск

1. Перейдите в каталог бота  
`cd bot`

2.1. Активируйте окружние и запустите сценарий **bot.py**  
```source python_env/bin/activate
python3 bot.py```  

2.2. Для запуска сценария без активации окружения  
`python_env/bin/python3 bot.py`

2.3. Для постоянной работы лучше запустить бота, как сервис

2.3.1. Создайте файл сервиса   
`nano /lib/systemd/system/bot.service`

```
[Unit]
  Description=bot
 
[Service]
  WorkingDirectory=/home/<username>/bot
  ExecStart=/home/<username>/bot/python_env/bin/python3 /home/<username>/bot/bot.py
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

2.3.2. Обновите список сервисов и запустите сервис **bot**  
```systemctl daemon-reload
systemctl start bot
systemctl enable bot```

## Мониторинг

1. Мониторинг журнала **systemd**  
`journalctl -f -u bot`

2. Слежение за файлом **bot.log**  
`tail --follow bot/bot.log`