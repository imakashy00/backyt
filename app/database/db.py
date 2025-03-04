import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
load_dotenv()

# Get database URL with a fallback
DATABASE_URI = os.getenv("DATABASE_URI")

# Add validation to ensure DATABASE_URL is not None
if not DATABASE_URI:
    raise ValueError("DATABASE_URL environment variable is not set")


engine  = create_engine(DATABASE_URI,echo= True,pool_pre_ping=True)
SessionLocal = sessionmaker(bind = engine, autocommit = False, autoflush = False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

