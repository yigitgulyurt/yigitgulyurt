import os
import json
from dotenv import load_dotenv

load_dotenv()

class Config:
    ADMIN_PASSWORD_HASH            = os.environ.get('ADMIN_PASSWORD_HASH')
    ADMIN_USERNAME                 = os.environ.get('ADMIN_USERNAME')       or 'admin'
    CONTACT_EMAIL                  = os.environ.get('CONTACT_EMAIL')        or 'yigit@yigitgulyurt.net.tr'
    MAX_CONTENT_LENGTH             = None  # Sınırsız - Nginx tarafında yönetilir
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

    # Cookie Güvenlik Ayarları
    SESSION_COOKIE_SECURE    = (os.environ.get('FLASK_ENV') == 'production')
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE  = 'Lax'
    REMEMBER_COOKIE_SECURE   = (os.environ.get('FLASK_ENV') == 'production')
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_DURATION = 86400  # 1 gün

    # WTF_CSRF_ENABLED       = True
    WTF_CSRF_TIME_LIMIT    = 3600  # 1 saat
    WTF_CSRF_SSL_STRICT    = (os.environ.get('FLASK_ENV') == 'production')

    # İzin verilen dosya yükleme uzantıları (kişisel dosyalar için — kişisel depo olduğundan geniş tutuldu)
    ALLOWED_EXTENSIONS = {
        # Belgeler
        'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'markdown', 'csv', 'json', 'xml',
        'html', 'htm', 'css', 'js', 'ts', 'tsx', 'jsx', 'svelte', 'vue', 'rtf', 'odt', 'ods', 'odp',
        # Görseller
        'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'bmp', 'ico', 'avif', 'tiff', 'tif', 'heic', 'heif', 'raw', 'cr2', 'nef', 'arw',
        # Videolar
        'mp4', 'webm', 'mov', 'avi', 'mkv', 'mpg', 'mpeg', 'm4v', 'flv', 'wmv', '3gp', 'ogv', 'h264', 'hevc',
        # Sesler
        'mp3', 'wav', 'flac', 'ogg', 'oga', 'm4a', 'aac', 'opus', 'wma', 'aiff', 'aif', 'amr', 'mid', 'midi',
        # Arşivler
        'zip', 'rar', '7z', 'tar', 'gz', 'tgz', 'bz2', 'xz', 'zst', 'lz', 'lzma', 'cab', 'iso',
        # Fontlar
        'ttf', 'otf', 'woff', 'woff2', 'eot',
        # Kod ve metin tabanlı
        'sql', 'log', 'yml', 'yaml', 'toml', 'cfg', 'ini', 'env', 'sh', 'bash', 'zsh',
        'bat', 'cmd', 'ps1', 'psm1', 'c', 'h', 'cpp', 'hpp', 'cs', 'java', 'kt', 'kts', 'go', 'rs',
        'rb', 'php', 'pl', 'lua', 'vim', 'conf', 'nginx', 'dockerfile', 'makefile', 'swift', 'dart',
        'scala', 'r', 'm', 'mm', 'gradle', 'exs', 'ex', 'hs', 'ml', 'clj', 'fs', 'fsx',
        # Diğer
        'epub', 'mobi', 'azw', 'azw3', 'cbz', 'cbr',
        'ics', 'vcf', 'pem', 'cer', 'crt', 'key', 'pub', 'asc', 'gpg',
        'torrent', 'srt', 'ass', 'sub', 'vtt',
    }
    MAX_UPLOAD_SIZE = None  # Sınırsız (chunked upload ile çok büyük dosyalar)
    PERSONAL_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'instance', 'personal_uploads')
    PERSONAL_UPLOAD_PARTIAL_FOLDER = os.path.join(os.path.dirname(__file__), 'instance', 'personal_uploads', '.partials')
    SHARE_TOKEN_LENGTH = 28
    RESUMABLE_CHUNK_MIN_SIZE = 1024 * 1024       # 1 MB minimum
    RESUMABLE_CHUNK_DEFAULT_SIZE = 8 * 1024 * 1024  # 8 MB (önerilen)

    # Telegram Bot Settings
    TELEGRAM_TOKEN                 = os.environ.get('TELEGRAM_TOKEN')
    ADMIN_TELEGRAM_ID              = os.environ.get('ADMIN_TELEGRAM_ID')

    # Wake-on-LAN Relay Settings
    WAKE_VPS_SECRET                = os.environ.get('WAKE_VPS_SECRET')    or ''
    WAKE_RELAY_URL                 = os.environ.get('WAKE_RELAY_URL')     or 'http://x.x.x.x:xxxx/wake'
    WAKE_RELAY_TOKEN               = os.environ.get('WAKE_RELAY_TOKEN')   or ''

    PC_CONTROL_HOST = os.environ.get("PC_CONTROL_HOST", "100.x.x.x")  # Windows PC'nin Tailscale IP'si
    PC_CONTROL_USER = os.environ.get("PC_CONTROL_USER", "kullanici")
    PC_CONTROL_SSH_KEY = os.environ.get("PC_CONTROL_SSH_KEY", "/home/yigitgulyurt/.ssh/pc_control")
    _raw_commands = os.environ.get("PC_ALLOWED_COMMANDS", "{}")
    try:
        PC_ALLOWED_COMMANDS = json.loads(_raw_commands)
    except json.JSONDecodeError:
        PC_ALLOWED_COMMANDS = {}