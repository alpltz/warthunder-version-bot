import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = os.getenv("ADMIN_ID", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@WarThunder_Game")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "15"))
ENABLE_CHANNEL_POST = os.getenv("ENABLE_CHANNEL_POST", "true").lower() == "true"

# Ссылки для мониторинга
URLS = {
    "Live": "https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=",
    "WiP": "https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=production-rc",
    "Dev": "https://yupmaster.gaijinent.com/yuitem/get_version.php?proj=warthunder&tag=dev",
}

# Файлы хранения
VERSIONS_FILE = "versions.json"
SUBSCRIBERS_FILE = "subscribers.json"
CONFIG_FILE = "bot_config.json"
