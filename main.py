from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date ,timedelta
from sqlalchemy import func
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine, sessionLocal
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
origins = [
    "http://localhost:4200",  # frontend URL
    "https://expense-front-one.vercel.app/",
    # Add other origins as needed
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,              # OR use ["*"] to allow all origins (not secure)
    allow_credentials=True,
    allow_methods=["*"],                # Allow all HTTP methods
    allow_headers=["*"],                # Allow all headers
)
# Dependency
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()

# ➕ Add a new expense
@app.post("/expenses/", response_model=schemas.ExpenseOut)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = models.Expense(**expense.dict())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

# 📄 List all expenses (with optional date filter)
@app.get("/expenses/", response_model=List[schemas.ExpenseOut])
def read_expenses(
    db: Session = Depends(get_db),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
):
    query = db.query(models.Expense)
    if from_date:
        query = query.filter(models.Expense.date >= from_date)
    if to_date:
        query = query.filter(models.Expense.date <= to_date)
    return query.all()

# ❌ Delete an expense by ID
@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()
    return {"detail": "Expense deleted"}


@app.get("/expenses/summary/monthly")
def monthly_summary(
    year: int = Query(..., example=2025),
    month: int = Query(..., example=6),
    db: Session = Depends(get_db)
):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    total = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.date >= start_date,
        models.Expense.date < end_date
    ).scalar() or 0.0

    return {
        "year": year,
        "month": month,
        "total_expense": round(total, 2)
    }

@app.get("/expenses/summary/weekly")
def weekly_summary(
    year: int = Query(..., example=2025),
    week: int = Query(..., example=23),
    db: Session = Depends(get_db)
):
    start_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").date()
    end_date = start_date + timedelta(days=7)

    total = db.query(func.sum(models.Expense.amount)).filter(
        models.Expense.date >= start_date,
        models.Expense.date < end_date
    ).scalar() or 0.0

    return {
        "year": year,
        "week": week,
        "total_expense": round(total, 2)
    }

@app.get("/expenses/summary/last-month-category")
def category_summary_last_month(db: Session = Depends(get_db)):
    today = date.today()
    first_day_this_month = date(today.year, today.month, 1)
    # Pichhla mahina ke last din tak ka date nikalo
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = date(last_day_last_month.year, last_day_last_month.month, 1)

    results = db.query(
        models.Expense.category,
        func.sum(models.Expense.amount)
    ).filter(
        models.Expense.date >= first_day_last_month,
        models.Expense.date <= last_day_last_month
    ).group_by(
        models.Expense.category
    ).all()

    return {
        "month": first_day_last_month.strftime("%B %Y"),
        "category_wise_total": [
            {"category": category, "total": round(total, 2)} for category, total in results
        ]
    }
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)