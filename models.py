from sqlalchemy import Column, String, Float, Boolean, Integer
from database import Base


class EligibleCustomer(Base):
    __tablename__ = "eligible_customers"

    id = Column(Integer, primary_key=True, index=True)
    msisdn = Column(String(15), unique=True, index=True)
    loan_limit = Column(Float)
    subscribed = Column(Boolean, default=False)
    loan_amount = Column(Float, nullable=True)


class USSD_Session(Base):
    __tablename__ = "ussd_sessions"

    session_id = Column(String(50), primary_key=True, index=True)
    msisdn = Column(String(15))
    service_code = Column(String(10))
    current_step = Column(String(20))