from fastapi import FastAPI, Depends
from app.db.session import get_db
from app.db import models
from sqlalchemy.orm import Session
from app.routers import auth, reviews, services, users, booking
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BookIt API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your frontend URL(s)
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],   # Accept all headers
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the BookIt API"}

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(services.router)
app.include_router(booking.router)
app.include_router(reviews.router)

# Example endpoint: list users (even if table is empty)
@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return users