from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()

# Render.com provides DATABASE_URL for Postgres. SQLite is used locally.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

# SQLAlchemy requires 'postgresql://' instead of 'postgres://' which Render might provide
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Float, default=0.0)
    api_key = Column(String, unique=True, index=True, nullable=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    service = Column(String)
    qty = Column(Integer)
    price = Column(Float)
    status = Column(String, default="Pending")
    external_id = Column(String, nullable=True)
    external_service_id = Column(String, nullable=True)
    remains = Column(Integer, default=0)
    start_count = Column(Integer, default=0)

class APISettings(Base):
    __tablename__ = "api_settings"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String)
    api_url = Column(String)
    api_key = Column(String)

class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    category = Column(String)
    price_per_1k = Column(Float)
    external_service_id = Column(String) # The ID used by the provider API
    min_qty = Column(Integer, default=100)
    max_qty = Column(Integer, default=10000)
    description = Column(String, default="Premium xizmat turi")
    average_time = Column(String, default="1-24 soat")

class PaymentRequest(Base) :
    __tablename__ = "payment_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float)
    method = Column(String) # click, payme, bankomat
    status = Column(String, default="Pending") # Pending, Approved, Rejected
    receipt_path = Column(String, nullable=True) # Path to uploaded chek
    timestamp = Column(String) # ISO format or simple string

class PaymentSettings(Base):
    __tablename__ = "payment_settings"
    id = Column(Integer, primary_key=True, index=True)
    method = Column(String, unique=True) # click, payme, bankomat
    card_number = Column(String, nullable=True)
    merchant_id = Column(String, nullable=True)
    title = Column(String)
    instructions = Column(String)

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String)
    message = Column(String)
    attachment_path = Column(String, nullable=True) # For rasm/video
    status = Column(String, default="Open") # Open, Answered, Closed
    timestamp = Column(String)
    admin_reply = Column(String, nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)
