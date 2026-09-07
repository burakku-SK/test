from sqlalchemy import Column, Integer, String, Boolean
from database import Base

class ExpenseModel(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)  # "YYYY-MM-DD"
    item = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)

class MemoModel(Base):
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True)
    content = Column(String, nullable=True)

class CheckListModel(Base):
    __tablename__ = "checklists"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    text = Column(String, nullable=False)
    checked = Column(Boolean, default=False)

# models.py の末尾に追加

class MonthlyPlanModel(Base):
    __tablename__ = "monthly_plans"

    month = Column(String, primary_key=True, index=True) # 例: "2026-09"
    income = Column(Integer, default=0)
    fixed = Column(Integer, default=0)
    budget = Column(Integer, default=0)

class ConfigModel(Base):
    __tablename__ = "configs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    targetGoal = Column(Integer, default=0)
    dangerThreshold = Column(Integer, default=0)
    payday = Column(Integer, default=15)