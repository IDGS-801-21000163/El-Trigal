import os
from pathlib import Path


def load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()

class Config(object):
    SECRET_KEY = "ClaveSecreta"
    SESSION_COOKIE_SECURE = False
    SESSION_INACTIVITY_MINUTES = int(os.getenv("SESSION_INACTIVITY_MINUTES", "10"))
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() == "true"
    # Desarrollo/QA: redirige correos enviados a un dominio a un buzón fijo.
    # Por defecto, cualquier envio a *@eltrigal.mx se redirige a messalejandro@gmail.com.
    MAIL_REDIRECT_DOMAIN = os.getenv("MAIL_REDIRECT_DOMAIN", "eltrigal.mx").strip().lower()
    MAIL_REDIRECT_TO = os.getenv("MAIL_REDIRECT_TO", "messalejandro@gmail.com").strip()
    OTP_EXPIRATION_MINUTES = int(os.getenv("OTP_EXPIRATION_MINUTES", "10"))
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    AZURE_OPENAI_REALTIME_DEPLOYMENT = os.getenv("AZURE_OPENAI_REALTIME_DEPLOYMENT")
    AZURE_OPENAI_REALTIME_VOICE = os.getenv("AZURE_OPENAI_REALTIME_VOICE", "alloy")
    AZURE_OPENAI_REALTIME_REGION = os.getenv("AZURE_OPENAI_REALTIME_REGION")
    AZURE_OPENAI_VISION_DEPLOYMENT = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT")
    AZURE_OPENAI_ASSISTANT_DEPLOYMENT = os.getenv(
        "AZURE_OPENAI_ASSISTANT_DEPLOYMENT",
        os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT"),
    )
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
    AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
    AZURE_SPEECH_VOICE = os.getenv("AZURE_SPEECH_VOICE", "es-MX-DaliaNeural")
    MONGO_URI = os.getenv("MONGO_URI")
    MONGO_DB = os.getenv("MONGO_DB", "panaderia")
    MONGO_LOG_COLLECTION = os.getenv("MONGO_LOG_COLLECTION", "app_logs")
    MONGO_AUDIT_COLLECTION = os.getenv("MONGO_AUDIT_COLLECTION", "audit_logs")

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://panaderia_app:ElTristeTigreDelTrigal!@127.0.0.1/panaderia'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
