import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

# Load .env file (works locally; Vercel uses its own env vars)
load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Fix old-style postgres:// URLs (Heroku/Render style)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# psycopg2 channel_binding parametrini qabul qilmaydi — olib tashlaymiz
if "channel_binding=require" in SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("&channel_binding=require", "")
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("?channel_binding=require&", "?")
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("?channel_binding=require", "")

is_vercel = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))
is_sqlite = False

if not SQLALCHEMY_DATABASE_URL:
    if is_vercel:
        # Vercel'da DATABASE_URL bo'lmasa — ma'lumotlar saqlanmaydi!
        # Bu yerda xato ko'rsatilsin, lekin tizim ishlasin
        print("CRITICAL ERROR: DATABASE_URL Vercel environment variables ga kiritilmagan!")
        print("Iltimos, Vercel Dashboard > Project Settings > Environment Variables ga DATABASE_URL qo'shing.")
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/sql_app.db"
        is_sqlite = True
    else:
        # Lokal ishlab chiqish uchun SQLite
        print("WARNING: DATABASE_URL topilmadi. Lokal SQLite ishlatilmoqda (sql_app.db).")
        SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
        is_sqlite = True
else:
    is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
    db_type = "SQLite" if is_sqlite else "PostgreSQL"
    print(f"Database: {db_type} ulandi.")

if is_sqlite:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL uchun connection pool sozlamalari
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # Ulanish sog'ligini tekshiradi
        pool_recycle=300,     # 5 daqiqada bir yangilaydi
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
