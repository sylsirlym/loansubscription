from fastapi import FastAPI
from .database import engine, Base
from . import main

# Initialize database models
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(main.router)