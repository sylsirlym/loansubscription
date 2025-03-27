from sqlalchemy import Column, String, Float, Boolean, Integer, DateTime, func
from .database import Base
from datetime import datetime

class EligibleCustomer(Base):
    __tablename__ = "eligible_customers"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4','comment': 'Stores customer loan eligibility information'}

    id = Column(Integer, primary_key=True, index=True)
    msisdn = Column(String(20), unique=True, index=True, nullable=False,
                   comment="Mobile subscriber number in E.164 format")
    name = Column(String(20), unique=True, index=True, nullable=False,
                   comment="Customer name")
    loan_limit = Column(Float, nullable=False, comment="Maximum allowed loan amount")
    subscribed = Column(Boolean, default=False,
                      comment="Whether customer has subscribed to loan service")
    loan_amount = Column(Float, nullable=True, comment="Actual loan amount requested")
    created_at = Column(DateTime, server_default=func.now(),
                       comment="Record creation timestamp")
    updated_at = Column(DateTime, server_default=func.now(),
                       onupdate=func.now(), comment="Last update timestamp")

class USSD_Session(Base):
    __tablename__ = "ussd_sessions"
    __table_args__ = {'mysql_engine':'InnoDB', 'mysql_charset':'utf8mb4', 'comment': 'Tracks active USSD sessions'}

    session_id = Column(String(100), primary_key=True, index=True,
                       comment="Unique session identifier")
    msisdn = Column(String(15), index=True, nullable=False,
                   comment="Mobile subscriber number")
    service_code = Column(String(10), nullable=False,
                         comment="USSD service code (e.g., *123#)")
    current_step = Column(String(20), nullable=False,
                         comment="Current step in USSD flow")
    created_at = Column(DateTime, server_default=func.now(),
                       comment="Session creation timestamp")
    last_activity = Column(DateTime, server_default=func.now(),
                          onupdate=func.now(), comment="Last interaction time")