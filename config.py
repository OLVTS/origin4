import os

print("DEBUG RAW ADMIN_IDS:", repr(os.getenv("ADMIN_IDS")))

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

# Безопасный парсинг списка админов
try:
    ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
except ValueError as e:
    print("❌ Ошибка в ADMIN_IDS:", e)
    ADMIN_IDS = []

# ➕ Добавленная переменная по умолчанию (если нужно)
DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE", "user")
