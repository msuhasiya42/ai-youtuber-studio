# backend/init_db.py
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from app.db.session import engine, Base
from app.models.models import * # Import all your models so Base.metadata knows about them

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()