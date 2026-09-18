# War Thunder Version Monitor Bot

Телеграм-бот который **постоянно мониторит** версии War Thunder и мгновенно сообщает об обновлениях в личку и в канал.

Мониторит 3 ссылки:
- 🟢 **Live** - `https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=` (основная игра)
- 🟡 **WiP** - `https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=production-rc` (почти релиз)
- 🔴 **Dev** - `https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=dev` (дев-сервер)

Когда версия меняется - бот шлет:
- Лично тебе (и всем подписчикам)
- В телеграм-канал (например @WarThunder_Game) - если настроишь

---

### 🚀 Быстрый старт (2 минуты)

**1. Создай бота**
- Напиши @BotFather в телеграм
- `/newbot` -> придумай имя -> получи токен вида `123456:AAH...`

**2. Установи зависимости**
```bash
git clone <этот репозиторий>
cd warthunder-version-bot
pip install -r requirements.txt
cp .env.example .env
nano .env # вставь BOT_TOKEN
```

**3. Запусти**
```bash
python bot.py
```
Напиши боту `/start` - ты станешь админом и подпишешься на уведомления.

**Готово!** Теперь бот чекает версии каждые 15 секунд.

---

### 📢 Как подключить канал @WarThunder_Game

Чтобы бот постил в канал:

1. Добавь твоего бота в канал как **Администратора**
   - Зайди в канал -> Управление -> Администраторы -> Добавить
   - Дай право "Публикация сообщений"

2. В боте напиши:
   ```
   /setchannel @WarThunder_Game
   ```
   Или если канал приватный - ID вида `-1001234567890` (узнать через @userinfobot или @getidsbot)

3. Проверь: бот отправит тестовое сообщение в канал. Если ошибка - значит не админ.

Включить/выключить постинг в канал: `/togglechannel`

---

### ⚙️ Команды бота

**Для всех:**
- `/start` - запуск, подписка
- `/status` - текущие версии Live/WiP/Dev прямо сейчас
- `/check` - форсированно проверить (не ждать таймера)
- `/subscribe` / `/unsubscribe` - подписка/отписка
- `/history` - последние известные версии
- `/help` - помощь

**Только для админа:**
- `/setchannel @name` - задать канал
- `/togglechannel` - вкл/выкл посты в канал
- `/setinterval 10` - интервал проверки в секундах (минимум 5)
- `/subscribers` - список подписчиков
- `/broadcast текст` - рассылка всем подписчикам

---

### 🐳 Запуск через Docker (для сервера)

```bash
cp .env.example .env
# отредактируй .env
docker-compose up -d --build
docker-compose logs -f
```

### 🔧 Запуск как сервис (Linux systemd)

Создай файл `/etc/systemd/system/wtbot.service`:

```ini
[Unit]
Description=War Thunder Version Bot
After=network.target

[Service]
WorkingDirectory=/home/user/warthunder-version-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
User=youruser

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable wtbot
sudo systemctl start wtbot
sudo journalctl -u wtbot -f
```

---

### 📁 Файлы

- `bot.py` - основной код
- `config.py` - настройки и ссылки
- `versions.json` - последние версии (создается автоматически)
- `subscribers.json` - подписчики
- `bot_config.json` - настройки канала и интервала
- `.env` - токен и настройки

### ⚡ Как это работает

1. Каждые N секунд (по умолчанию 15) бот делает GET запрос к 3 URL
2. Сравнивает с предыдущим значением из `versions.json`
3. Если изменилось - формирует красивое сообщение с diff
4. Рассылает всем подписчикам + в канал
5. Сохраняет новую версию

Интервал 5-15 секунд - максимально быстро насколько возможно без бана. Gaijin не блокирует такие запросы, но не ставь меньше 5 сек.

### 🛡️ Надежность

- Если Gaijin не отвечает - бот не крашится, просто ждет следующую проверку
- Если юзер заблокировал бота - автоматически удаляется из подписчиков
- Если не удалось отправить в канал - пишет админу в ЛС
- Логи в консоли

Хочешь добавить вебхуки, базу данных или парсинг чейнджлога? Скажи - допилю.

