from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment variable or use default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/compliance_db")

# IF the database url is loaded from the environment variable, then inform user if the default is being used then inform user
if DATABASE_URL == "postgresql://postgres:postgres@localhost:5432/compliance_db":
    print("Couldn't find the Database URL in the environment variable, using default database URL")
else:
    print("Using the Database URL from the environment variable")


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 