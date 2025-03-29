import os
from fastapi import APIRouter, Response, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import get_db
from .models import EligibleCustomer, USSD_Session
from .service import Service
from sqlalchemy.exc import OperationalError
from typing import Optional
import traceback
import pandas as pd
import tempfile
import logging
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
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

# USSD Endpoint
@router.api_route("/ussd", methods=["GET", "POST"], response_class=Response)
async def ussd(
        session_id: str = Query(..., alias="session_id"),
        msisdn: str = Query(..., alias="msisdn"),
        service_code: str = Query(..., alias="service_code"),
        ussd_string: str = Query(..., alias="ussd_string"),
        db: Session = Depends(get_db)):
    logger.info(
        f"Received USSD request - Session ID:[{session_id}], MSISDN: [{msisdn}], Service Code: [{service_code}], USSD String: [{ussd_string}]")

    try:
        # Check if session exists
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

        # Lookup customer by MSISDN
        customer = db.query(EligibleCustomer).filter(EligibleCustomer.msisdn == msisdn).first()

        # Step 1: Welcome message
        if session.current_step == "welcome":
            if customer:
                customer_name = customer.name
                response = f"Hello {customer_name}, welcome! Would you like to know your loan limit?\n1. Yes\n2. No"
                session.current_step = "loan_limit_choice"
            else:
                response = "Please enter your name to proceed."
                session.current_step = "register_customer"

            db.commit()
            return Response(content=f"CON {response}", media_type="text/plain")

        # Step 2: Register new customer
        elif session.current_step == "register_customer":
            new_customer = EligibleCustomer(
                name=ussd_string.strip(),
                msisdn=msisdn,
                loan_limit=0,
                subscribed=True
            )
            db.add(new_customer)
            db.commit()
            return Response(
                content="END Thank you! You have been registered. Please dial again to check your loan limit.",
                media_type="text/plain")

        # Step 3: Loan limit inquiry
        elif session.current_step == "loan_limit_choice":
            if ussd_string == "1":
                if not customer:
                    return Response(content="END Customer not found.", media_type="text/plain")

                customer.subscribed = True
                db.commit()

                response = f"Your loan limit is {customer.loan_limit}. Would you like to request a loan?\n1. Yes\n2. No"
                session.current_step = "loan_request_choice"
                db.commit()
                return Response(content=f"CON {response}", media_type="text/plain")

            elif ussd_string == "2":
                return Response(content="END Thanks for using our service.", media_type="text/plain")

        # Step 4: Loan request
        elif session.current_step == "loan_request_choice":
            if ussd_string == "1":
                response = "Enter Loan Amount"
                session.current_step = "loan_amount_input"
                db.commit()
                return Response(content=f"CON {response}", media_type="text/plain")

            elif ussd_string == "2":
                return Response(content="END Thanks for using our service.", media_type="text/plain")

        # Step 5: Loan amount input
        elif session.current_step == "loan_amount_input":
            try:
                loan_amount = float(ussd_string)
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


@router.post("/upload-excel/")
async def upload_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Please upload an Excel file")
    logger.info(f"Received Excel file - File name: [{file.filename}]")
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.file.read())
            tmp_path = tmp.name
        df = pd.read_excel(tmp_path,engine="openpyxl")
        df.fillna("", inplace=True)
        eligible_customers = df.to_dict("records")

        created_profiles = []
        for eligible_customer in eligible_customers:
            msisdn = str(eligible_customer.get("Phone", "")).strip()
            if not msisdn:
                continue  # Skip record if msisdn is empty or null

            customer = EligibleCustomer(
                name=eligible_customer.get("Name", ""),
                loan_limit=float(eligible_customer.get("Amount", 0)),
                msisdn=msisdn
            )

            existing_customer = db.query(EligibleCustomer).filter(EligibleCustomer.msisdn == customer.msisdn).first()
            if not existing_customer:
                db.add(customer)
                created_profiles.append(customer)

                # Send SMS after inserting the record
                message_template = os.getenv("SMS_TEMPLATE")
                customer_name = customer.name if customer.name else "Customer"
                message = message_template.format(customer=customer_name, token=customer.token)
                Service.send_message(customer.msisdn, message)

        db.commit()

        return {
            "message": f"Successfully uploaded {len(created_profiles)} profiles",
            "filename": file.filename
        }

    except Exception as e:
        error_message = f"Exception occurred while processing Excel file: {str(e)}"
        stack_trace = traceback.format_exc()
        logger.error(f"{error_message}\nStack Trace:\n{stack_trace}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

    finally:
        file.file.close()


@router.get("/details/{token}")
async def get_offer(
        token: str,
        db: Session = Depends(get_db)
):
    customer = db.query(EligibleCustomer).filter(
        EligibleCustomer.token == token
    ).first()

    if not customer:
        raise HTTPException(404, "Customer not found")

    return {
        "name": customer.name,
        "msisdn": customer.msisdn,
        "loanLimit": customer.loan_limit,
    }

def safe_float(value):
    try:
        return float(value)
    except Exception as e:
        error_message = f"Exception occurred while processing creating a float: {str(e)}"
        stack_trace = traceback.format_exc()
        logger.error(f"{error_message}\nStack Trace:\n{stack_trace}")
        return 0