import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
load_dotenv()

DATABASE_URI = os.getenv('DATABASE_URI')

engine  = create_engine(DATABASE_URI,echo= True,pool_pre_ping=True)
SessionLocal = sessionmaker(bind = engine, autocommit = False, autoflush = False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

