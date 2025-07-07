from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import date, timedelta, datetime
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine, async_session
import schemas

app = FastAPI()

# ✅ Create tables asynchronously on app startup
@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# ✅ CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ✅ Dependency to get DB session
async def get_db():
    async with async_session() as session:
        yield session

# ➕ Add a new expense
@app.post("/expenses/", response_model=schemas.ExpenseOut)
async def create_expense(expense: schemas.ExpenseCreate, db: AsyncSession = Depends(get_db)):
    db_expense = models.Expense(**expense.dict())
    db.add(db_expense)
    await db.commit()
    await db.refresh(db_expense)
    return db_expense

# 📄 List all expenses (with optional date filter)
@app.get("/expenses/", response_model=List[schemas.ExpenseOut])
async def read_expenses(
    db: AsyncSession = Depends(get_db),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None
):
    query = select(models.Expense)
    if from_date:
        query = query.where(models.Expense.date >= from_date)
    if to_date:
        query = query.where(models.Expense.date <= to_date)

    result = await db.execute(query)
    return result.scalars().all()

# ❌ Delete an expense by ID
@app.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.Expense).where(models.Expense.id == expense_id))
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    await db.delete(expense)
    await db.commit()
    return {"detail": "Expense deleted"}

# 📆 Monthly summary
@app.get("/expenses/summary/monthly")
async def monthly_summary(
    year: int = Query(..., example=2025),
    month: int = Query(..., example=6),
    db: AsyncSession = Depends(get_db)
):
    start_date = date(year, month, 1)
    end_date = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)

    result = await db.execute(
        select(func.sum(models.Expense.amount)).where(
            models.Expense.date >= start_date,
            models.Expense.date < end_date
        )
    )
    total = result.scalar() or 0.0

    return {
        "year": year,
        "month": month,
        "total_expense": round(total, 2)
    }

# 📆 Weekly summary
@app.get("/expenses/summary/weekly")
async def weekly_summary(
    year: int = Query(..., example=2025),
    week: int = Query(..., example=23),
    db: AsyncSession = Depends(get_db)
):
    start_date = datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w").date()
    end_date = start_date + timedelta(days=7)

    result = await db.execute(
        select(func.sum(models.Expense.amount)).where(
            models.Expense.date >= start_date,
            models.Expense.date < end_date
        )
    )
    total = result.scalar() or 0.0

    return {
        "year": year,
        "week": week,
        "total_expense": round(total, 2)
    }

# 📊 Category-wise summary for last month
@app.get("/expenses/summary/last-month-category")
async def category_summary_last_month(db: AsyncSession = Depends(get_db)):
    today = date.today()
    first_day_this_month = date(today.year, today.month, 1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = date(last_day_last_month.year, last_day_last_month.month, 1)

    result = await db.execute(
        select(models.Expense.category, func.sum(models.Expense.amount))
        .where(models.Expense.date >= first_day_last_month, models.Expense.date <= last_day_last_month)
        .group_by(models.Expense.category)
    )

    results = result.all()

    return {
        "month": first_day_last_month.strftime("%B %Y"),
        "category_wise_total": [
            {"category": category, "total": round(total, 2)} for category, total in results
        ]
    }
