#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
War Thunder Version Monitor Bot
Мониторит Live / WiP / Dev версии и шлет в ЛС + в канал @WarThunder_Game
"""

import asyncio
import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import config

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Хранилище ---
def load_json(path, default):
    if Path(path).exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return default
    return default

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Состояние ---
last_versions = load_json(config.VERSIONS_FILE, {})
subscribers = set(load_json(config.SUBSCRIBERS_FILE, []))
bot_config = load_json(config.CONFIG_FILE, {
    "channel_id": config.CHANNEL_ID,
    "interval": config.CHECK_INTERVAL,
    "enable_channel": config.ENABLE_CHANNEL_POST
})

admin_id = None
if config.ADMIN_ID and config.ADMIN_ID.isdigit():
    admin_id = int(config.ADMIN_ID)

# --- Fetch ---
async def fetch_version(session: aiohttp.ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            text = await resp.text()
            return text.strip()
    except Exception as e:
        logger.warning(f"Ошибка запроса {url}: {e}")
        return None

async def get_all_versions():
    results = {}
    async with aiohttp.ClientSession(headers={"User-Agent": "WT-Version-Bot/1.0"}) as session:
        tasks = {name: fetch_version(session, url) for name, url in config.URLS.items()}
        for name, coro in tasks.items():
            results[name] = await coro
    return results

def format_version_message(name, old, new, is_initial=False):
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    emoji_map = {"Live": "🟢", "WiP": "🟡", "Dev": "🔴"}
    emoji = emoji_map.get(name, "⚪️")

    if is_initial:
        return (
            f"{emoji} <b>{name} версия War Thunder</b>\n"
            f"<code>{new}</code>\n"
            f"⏰ {now}"
        )
    else:
        return (
            f"🚨 <b>ОБНОВЛЕНИЕ War Thunder!</b> 🚨\n\n"
            f"{emoji} <b>{name}:</b> <code>{old}</code> → <code>{new}</code>\n\n"
            f"⏰ Время: {now} (MSK)\n"
            f"🔗 <a href='{config.URLS[name]}'>Проверить источник</a>\n\n"
            f"#WarThunder #{name} #{new.replace('.', '_')}"
        )

async def check_and_notify(app):
    global last_versions
    logger.info("Проверка версий...")
    current = await get_all_versions()
    
    changes = []
    for name, ver in current.items():
        if not ver:
            continue
        old = last_versions.get(name)
        if old is None:
            # Первый запуск
            logger.info(f"Инициализация {name}: {ver}")
            changes.append((name, None, ver, True))
            last_versions[name] = ver
        elif old != ver:
            logger.info(f"ДЕТЕКТ! {name}: {old} -> {ver}")
            changes.append((name, old, ver, False))
            last_versions[name] = ver

    if changes:
        save_json(config.VERSIONS_FILE, last_versions)
        # Отправляем уведомления
        for name, old, new, is_initial in changes:
            if is_initial and len(last_versions) != 1:
                # Не спамим инициализацией если уже есть данные, только если это самый первый запуск
                # Но для первого запуска всего бота - отправим статус
                pass
            
            msg = format_version_message(name, old, new, is_initial=False if old else False)
            if old is None and len([k for k in last_versions.values() if k]) > 1:
                # Пропускаем initial сообщения при рестарте если версии уже были
                continue

            # Если это initial запуск (файла не было) - отправим красивое стартовое сообщение
            if old is None:
                msg = (
                    f"✅ <b>Бот запущен. Текущие версии:</b>\n\n"
                    + "\n".join([f"{'🟢' if k=='Live' else '🟡' if k=='WiP' else '🔴'} <b>{k}:</b> <code>{v}</code>" for k,v in last_versions.items()])
                )
                # Отправим только один раз для всех initial
                if name != list(current.keys())[0]:
                    continue

            # 1. Всем подписчикам
            for chat_id in list(subscribers):
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить {chat_id}: {e}")
                    # Если юзер заблокировал бота - можно удалить
                    if "blocked" in str(e).lower() or "chat not found" in str(e).lower():
                        subscribers.discard(chat_id)
                        save_json(config.SUBSCRIBERS_FILE, list(subscribers))

            # 2. В канал
            if bot_config.get("enable_channel") and bot_config.get("channel_id"):
                try:
                    await app.bot.send_message(
                        chat_id=bot_config["channel_id"],
                        text=msg,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                    logger.info(f"Отправлено в канал {bot_config['channel_id']}")
                except Exception as e:
                    logger.error(f"Ошибка отправки в канал {bot_config['channel_id']}: {e}")
                    # Сообщим админу
                    if admin_id:
                        try:
                            await app.bot.send_message(
                                admin_id,
                                f"⚠️ Не смог отправить в канал {bot_config['channel_id']}:\n<code>{e}</code>\n\n"
                                f"Проверь что бот добавлен в админы канала!",
                                parse_mode=ParseMode.HTML
                            )
                        except:
                            pass

    return changes

# --- Background loop ---
async def monitor_loop(app):
    await asyncio.sleep(5) # Даем боту запуститься
    logger.info(f"Мониторинг запущен, интервал {bot_config.get('interval', 15)} сек")
    # Первичная инициализация если файла нет
    if not last_versions:
        await check_and_notify(app)
    while True:
        try:
            interval = bot_config.get("interval", config.CHECK_INTERVAL)
            await check_and_notify(app)
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception(f"Ошибка в monitor_loop: {e}")
            await asyncio.sleep(10)

# --- Команды ---

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_id
    chat_id = update.effective_chat.id
    
    # Авто-назначение админа если не задан
    if admin_id is None:
        admin_id = chat_id
        # Сохраним в .env для удобства (не обязательно)
        logger.info(f"Новый админ назначен: {admin_id}")
        await update.message.reply_text(
            f"👑 Ты назначен админом бота! Твой ID: <code>{admin_id}</code>\n"
            f"Добавь его в .env как ADMIN_ID чтобы сохранить после рестарта.",
            parse_mode=ParseMode.HTML
        )

    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_json(config.SUBSCRIBERS_FILE, list(subscribers))

    await update.message.reply_text(
        "👋 <b>War Thunder Version Monitor</b>\n\n"
        "Я мониторю версии игры каждые 15 секунд:\n"
        "🟢 <b>Live</b> - основная игра\n"
        "🟡 <b>WiP</b> - production-rc (скоро в релиз)\n"
        "🔴 <b>Dev</b> - дев сервер\n\n"
        "Команды:\n"
        "/status - текущие версии\n"
        "/check - проверить сейчас\n"
        "/subscribe - подписаться на уведомления\n"
        "/unsubscribe - отписаться\n"
        "/history - последние версии\n"
        "/help - помощь\n\n"
        f"📢 Канал для постов: {bot_config.get('channel_id')}\n"
        f"⏱ Интервал: {bot_config.get('interval')} сек\n\n"
        "Ты уже подписан на уведомления!",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current = await get_all_versions()
    now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lines = [f"📊 <b>Статус на {now}</b>\n"]
    for name in ["Live", "WiP", "Dev"]:
        ver = current.get(name) or last_versions.get(name) or "❓ нет данных"
        emoji = "🟢" if name=="Live" else "🟡" if name=="WiP" else "🔴"
        url = config.URLS[name]
        lines.append(f"{emoji} <b>{name}:</b> <code>{ver}</code> - <a href='{url}'>источник</a>")
    
    lines.append(f"\n⏱ Проверка каждые {bot_config.get('interval')} сек")
    lines.append(f"📢 Канал: {bot_config.get('channel_id')} ({'вкл' if bot_config.get('enable_channel') else 'выкл'})")
    lines.append(f"👥 Подписчиков: {len(subscribers)}")
    
    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Проверяю версии...")
    changes = await check_and_notify(context.application)
    if not changes:
        current = last_versions
        await update.message.reply_text(
            "✅ Изменений нет.\n" + 
            "\n".join([f"<b>{k}:</b> <code>{v}</code>" for k,v in current.items()]),
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(f"🚨 Найдено {len(changes)} изменений! Уведомления отправлены.")

async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        await update.message.reply_text("Ты уже подписан ✅")
    else:
        subscribers.add(chat_id)
        save_json(config.SUBSCRIBERS_FILE, list(subscribers))
        await update.message.reply_text("✅ Подписал тебя на уведомления об обновлениях!")

async def unsubscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in subscribers:
        subscribers.discard(chat_id)
        save_json(config.SUBSCRIBERS_FILE, list(subscribers))
        await update.message.reply_text("❌ Отписал от уведомлений.")
    else:
        await update.message.reply_text("Ты и так не подписан.")

async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not last_versions:
        await update.message.reply_text("Пока нет данных. Используй /check")
        return
    await update.message.reply_text(
        "📜 <b>Последние известные версии:</b>\n\n" +
        "\n".join([f"<b>{k}:</b> <code>{v}</code>" for k,v in last_versions.items()]),
        parse_mode=ParseMode.HTML
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Помощь по боту</b>\n\n"
        "/start - запуск и подписка\n"
        "/status - текущие версии Live/WiP/Dev\n"
        "/check - форсированная проверка\n"
        "/subscribe /unsubscribe - подписка\n"
        "/history - последние версии\n\n"
        "<b>Админ-команды:</b>\n"
        "/setchannel @username или ID - задать канал\n"
        "/togglechannel - вкл/выкл постинг в канал\n"
        "/setinterval 15 - интервал проверки в сек\n"
        "/subscribers - список подписчиков\n"
        "/broadcast текст - рассылка всем\n\n"
        "Чтобы бот постил в @WarThunder_Game:\n"
        "1. Добавь бота в канал как админа\n"
        "2. Дай права на постинг сообщений\n"
        "3. Установи /setchannel @WarThunder_Game\n",
        parse_mode=ParseMode.HTML
    )

# Админ команды
def is_admin(user_id):
    return admin_id is None or user_id == admin_id or user_id in subscribers and admin_id == user_id or user_id == admin_id

async def setchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_id
    if update.effective_user.id != admin_id and admin_id is not None:
        await update.message.reply_text("⛔ Только для админа.")
        return
    if not context.args:
        await update.message.reply_text(
            f"Текущий канал: {bot_config.get('channel_id')}\n"
            f"Использование: /setchannel @WarThunder_Game или /setchannel -1001234567890"
        )
        return
    new_channel = context.args[0]
    bot_config["channel_id"] = new_channel
    save_json(config.CONFIG_FILE, bot_config)
    await update.message.reply_text(f"✅ Канал установлен: {new_channel}\nТеперь проверю права...")

    # Тестовое сообщение
    try:
        await context.bot.send_message(
            chat_id=new_channel,
            text="✅ Бот подключен к каналу! Теперь сюда будут приходить обновления War Thunder.",
        )
        await update.message.reply_text("✅ Тестовое сообщение в канал отправлено успешно!")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Не смог отправить в {new_channel}:\n<code>{e}</code>\nПроверь что бот админ в канале.", parse_mode=ParseMode.HTML)

async def togglechannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id and admin_id is not None:
        await update.message.reply_text("⛔ Только для админа.")
        return
    bot_config["enable_channel"] = not bot_config.get("enable_channel", True)
    save_json(config.CONFIG_FILE, bot_config)
    await update.message.reply_text(f"📢 Постинг в канал: {'ВКЛ ✅' if bot_config['enable_channel'] else 'ВЫКЛ ❌'}")

async def setinterval_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id and admin_id is not None:
        await update.message.reply_text("⛔ Только для админа.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(f"Текущий интервал: {bot_config.get('interval')} сек\nИспользование: /setinterval 15")
        return
    interval = int(context.args[0])
    if interval < 5:
        await update.message.reply_text("⛔ Минимум 5 секунд чтобы не забанили IP.")
        return
    bot_config["interval"] = interval
    save_json(config.CONFIG_FILE, bot_config)
    await update.message.reply_text(f"✅ Интервал установлен: {interval} сек")

async def subscribers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id and admin_id is not None:
        await update.message.reply_text("⛔ Только для админа.")
        return
    await update.message.reply_text(f"👥 Подписчиков: {len(subscribers)}\n" + "\n".join([f"<code>{s}</code>" for s in list(subscribers)[:50]]), parse_mode=ParseMode.HTML)

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != admin_id and admin_id is not None:
        await update.message.reply_text("⛔ Только для админа.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /broadcast Текст сообщения")
        return
    text = " ".join(context.args)
    count = 0
    for chat_id in list(subscribers):
        try:
            await context.bot.send_message(chat_id=chat_id, text=f"📢 <b>Сообщение от админа:</b>\n\n{text}", parse_mode=ParseMode.HTML)
            count += 1
        except:
            pass
    await update.message.reply_text(f"✅ Разослано {count} пользователям.")

# --- Main ---
def main():
    load_dotenv()
    token = os.getenv("BOT_TOKEN") or config.BOT_TOKEN
    if not token:
        print("❌ BOT_TOKEN не задан! Создай .env из .env.example и вставь токен от @BotFather")
        return

    print(f"🚀 Запуск бота... Канал: {bot_config.get('channel_id')}, интервал: {bot_config.get('interval')}s")

    app = ApplicationBuilder().token(token).build()

    # Команды
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
    app.add_handler(CommandHandler("history", history_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("setchannel", setchannel_cmd))
    app.add_handler(CommandHandler("togglechannel", togglechannel_cmd))
    app.add_handler(CommandHandler("setinterval", setinterval_cmd))
    app.add_handler(CommandHandler("subscribers", subscribers_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))

    # Фоновый мониторинг
    async def on_startup(app):
        asyncio.create_task(monitor_loop(app))

    app.post_init = on_startup

    print("✅ Бот запущен. Нажми Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
