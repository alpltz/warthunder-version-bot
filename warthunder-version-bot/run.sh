#!/bin/bash
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  echo "❌ Нет .env файла! Копирую из .env.example"
  cp .env.example .env
  echo "Отредактируй .env и вставь BOT_TOKEN"
  exit 1
fi
pip install -r requirements.txt
python bot.py
