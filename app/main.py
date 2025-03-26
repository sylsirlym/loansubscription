from fastapi import APIRouter, Response, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import get_db
from .models import EligibleCustomer, USSD_Session
import psycopg2
from psycopg2 import OperationalError
from typing import Optional

router = APIRouter()

# Request Models
class USSDRequest(BaseModel):
    USSD_STRING: str
    SESSION_ID: str
    MSISDN: str
    SERVICE_CODE: str


class CustomerCreate(BaseModel):
    msisdn: str
    loan_limit: float
    subscribed: Optional[bool] = False
    loan_amount: Optional[float] = None


# Endpoint to create eligible customers
@router.post("/customers/", status_code=201)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    try:
        # Check if customer already exists
        existing_customer = db.query(EligibleCustomer).filter(
            EligibleCustomer.msisdn == customer.msisdn
        ).first()

        if existing_customer:
            raise HTTPException(
                status_code=400,
                detail="Customer with this MSISDN already exists"
            )

        # Create new customer
        db_customer = EligibleCustomer(
            msisdn=customer.msisdn,
            loan_limit=customer.loan_limit,
            subscribed=customer.subscribed,
            loan_amount=customer.loan_amount
        )

        db.add(db_customer)
        db.commit()
        db.refresh(db_customer)

        return {
            "message": "Customer created successfully",
            "msisdn": db_customer.msisdn,
            "loan_limit": db_customer.loan_limit
        }

    except OperationalError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )


# USSD Endpoint
@router.post("/ussd", response_class=Response)
async def ussd(request: USSDRequest, db: Session = Depends(get_db)):
    ussd_string = request.USSD_STRING.strip()
    session_id = request.SESSION_ID
    msisdn = request.MSISDN
    service_code = request.SERVICE_CODE

    try:
        session = db.query(USSD_Session).filter(USSD_Session.session_id == session_id).first()

        if not session:
            session = USSD_Session(
                session_id=session_id,
                msisdn=msisdn,
                service_code=service_code,
                current_step="welcome"
            )
            db.add(session)
            db.commit()

        if session.current_step == "welcome":
            response = "Welcome, would you like to know your loan limit?\n1. Yes\n2. No"
            session.current_step = "loan_limit_choice"
            db.commit()
            return Response(content=f"CON {response}", media_type="text/plain")

        elif session.current_step == "loan_limit_choice":
            if ussd_string == "1":
                customer = db.query(EligibleCustomer).filter(
                    EligibleCustomer.msisdn == msisdn
                ).first()

                if not customer:
                    return Response(content="END Customer not found.", media_type="text/plain")

                customer.subscribed = True
                db.commit()

                response = f"Your loan limit is {customer.loan_limit}. Would you like to request for a loan?\n1. Yes\n2. No"
                session.current_step = "loan_request_choice"
                db.commit()
                return Response(content=f"CON {response}", media_type="text/plain")

            elif ussd_string == "2":
                return Response(content="END Thanks for using our service.", media_type="text/plain")

        elif session.current_step == "loan_request_choice":
            if ussd_string == "1":
                response = "Enter Loan Amount"
                session.current_step = "loan_amount_input"
                db.commit()
                return Response(content=f"CON {response}", media_type="text/plain")

            elif ussd_string == "2":
                return Response(content="END Thanks for using our service.", media_type="text/plain")

        elif session.current_step == "loan_amount_input":
            try:
                loan_amount = float(ussd_string)
                customer = db.query(EligibleCustomer).filter(
                    EligibleCustomer.msisdn == msisdn
                ).first()

                if customer:
                    customer.loan_amount = loan_amount
                    db.commit()
                return Response(content="END Thanks for using our service.", media_type="text/plain")
            except ValueError:
                return Response(content="CON Invalid input. Please enter a valid loan amount.", media_type="text/plain")

        return Response(content="END Invalid input.", media_type="text/plain")

    except OperationalError as e:
        db.rollback()
        return Response(content="END Database connection error.", media_type="text/plain")
    finally:
        db.close()