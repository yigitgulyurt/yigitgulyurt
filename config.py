import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ADMIN_PASSWORD_HASH            = os.environ.get('ADMIN_PASSWORD_HASH')
    ADMIN_USERNAME                 = os.environ.get('ADMIN_USERNAME')       or 'admin'
    CONTACT_EMAIL                  = os.environ.get('CONTACT_EMAIL')        or 'yigit@yigitgulyurt.net.tr'
    MAX_CONTENT_LENGTH             = 5 * 1024 * 1024  # 5MB
    OBSIDIAN_PASSWORD              = os.environ.get('OBSIDIAN_PASSWORD')    or ''
    OBSIDIAN_VAULT_PATH            = os.environ.get('OBSIDIAN_VAULT_PATH')  or '/mnt/obsidian'
    REDIS_URL                      = os.environ.get('REDIS_URL')            or 'redis://localhost:6379/0'
    SECRET_KEY                     = os.environ.get('SECRET_KEY')           or 'dev-secret-change-in-prod'
    SERVER_NAME                    = os.environ.get('SERVER_NAME')          or 'yigitgulyurt.net.tr'
    SHOW_STREAM_SECTION            = (os.environ.get('SHOW_STREAM_SECTION') or 'false').lower() == 'true'
    SQLALCHEMY_DATABASE_URI        = os.environ.get('DATABASE_URL')         or 'sqlite:///yigitgulyurt.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STREAM_KEY                     = os.environ.get('STREAM_KEY')           or ''
    STREAM_LIVE_FALLBACK           = os.environ.get('STREAM_LIVE_FALLBACK') or 'false'
    UPLOAD_FOLDER                  = os.path.join(os.path.dirname(__file__), 'app', 'static', 'image', 'yigitgulyurt')

    # Telegram Bot Settings
    TELEGRAM_TOKEN                 = os.environ.get('TELEGRAM_TOKEN')
    ADMIN_TELEGRAM_ID              = os.environ.get('ADMIN_TELEGRAM_ID')