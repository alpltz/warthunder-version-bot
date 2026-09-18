@echo off
chcp 65001 >nul
title War Thunder Version Bot
cd /d "%~dp0"

echo ========================================
echo  War Thunder Version Monitor Bot
echo ========================================
echo.

if not exist .env (
    echo [X] Нет файла .env! Копирую из примера...
    copy .env.example .env
    echo.
    echo [!] Открой файл .env блокнотом и вставь BOT_TOKEN от @BotFather
    echo     Потом снова запусти этот файл.
    pause
    notepad .env
    exit /b
)

echo [1/3] Проверяю Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [X] Python не найден!
    echo.
    echo Скачай и установи Python с https://www.python.org/downloads/
    echo ВАЖНО: При установке поставь галочку "Add python.exe to PATH"
    echo.
    pause
    start https://www.python.org/downloads/
    exit /b
)
python --version

echo.
echo [2/3] Устанавливаю зависимости...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo [3/3] Запускаю бота...
echo     Не закрывай это окно! Бот работает пока оно открыто.
echo     Нажми Ctrl+C чтобы остановить.
echo.
python bot.py

pause
