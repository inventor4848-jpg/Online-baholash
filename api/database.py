import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Default to a local SQLite if DATABASE_URL is not set for initial testing, 
# but expect PostgreSQL URL from Neon.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not SQLALCHEMY_DATABASE_URL:
    # On Vercel, we MUST have a DATABASE_URL for persistence
    if os.getenv("VERCEL") or os.path.exists("/tmp"):
        print("CRITICAL: DATABASE_URL not found on Vercel. SQLite fallback is dangerous.")
        # We'll still set it to /tmp just in case, but we should log it
        SQLALCHEMY_DATABASE_URL = "sqlite:////tmp/sql_app.db"
    else:
        print("WARNING: DATABASE_URL not found. Using local SQLite.")
        SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if is_sqlite else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
