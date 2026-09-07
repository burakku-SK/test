from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, SessionLocal

# ディレクトリの絶対パスを取得
BASE_DIR = Path(__file__).resolve().parent

# DBテーブルの作成
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 静的ファイルの配信設定（1箇所に集約）
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DBセッション取得用依存関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Pydantic スキーマ定義 ---

class ExpenseCreate(BaseModel):
    date: str
    item: str
    amount: int

class MemoSave(BaseModel):
    date: str
    content: str

class CheckListCreate(BaseModel):
    date: str
    text: str

class CheckListUpdate(BaseModel):
    checked: bool

class Checklogin(BaseModel):
    username: str
    password: str

class MonthlySavedata(BaseModel):
    month: str
    income: int
    fixed: int
    budget: int

class MonthlyConfigSave(BaseModel):
    targetGoal: int
    dangerThreshold: int
    payday: int 


# --- API エンドポイント ---

# 0. ログイン用
@app.post("/api/login")
def check_login(data: Checklogin):
    user = "admin"
    password = "password"

    if data.username == user and data.password == password:
        return {"status": "success", "message": "ログイン成功"}
    raise HTTPException(status_code=401, detail="認証情報に誤りがあります")

# 1. 全データ取得 (初期読み込み用)
@app.get("/api/data")
def get_all_data(db: Session = Depends(get_db)):
    expenses = db.query(models.ExpenseModel).all()
    memos = db.query(models.MemoModel).all()
    checklists = db.query(models.CheckListModel).all()
    monthly_plans = db.query(models.MonthlyPlanModel).all() if hasattr(models, 'MonthlyPlanModel') else []
    config = db.query(models.ConfigModel).first() if hasattr(models, 'ConfigModel') else None

    # 支出データを日付ごとにグループ化
    daily_expenses = {}
    for E in expenses:
        if E.date not in daily_expenses:
            daily_expenses[E.date] = []
        daily_expenses[E.date].append({"id": E.id, "item": E.item, "amount": E.amount})
        
    # チェックリストデータを日付ごとにグループ化
    daily_checklists = {}
    for C in checklists:
        if C.date not in daily_checklists:
            daily_checklists[C.date] = []
        daily_checklists[C.date].append({"id": C.id, "text": C.text, "checked": C.checked})

    plans_dict = {}
    for p in monthly_plans:
        plans_dict[p.month] = {"income": p.income, "fixed": p.fixed, "budget": p.budget}

    # メモデータを辞書化（空文字以外のみ抽出）
    daily_memos = {m.date: m.content for m in memos if m.content and m.content.strip() != ""}

    # 設定値オブジェクト
    config_dict = {
        "targetGoal": config.targetGoal if config else 0,
        "dangerThreshold": config.dangerThreshold if config else 0,
        "payday": config.payday if config else 15
    }
    return {
        "dailyExpenses": daily_expenses,
        "dailyMemos": daily_memos,
        "dailyChecklists": daily_checklists,
        "monthlyPlans": plans_dict, 
        "config": config_dict
    }


# 2. 支出 (Expenses) API
@app.post("/api/expenses")
def add_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    db_item = models.ExpenseModel(date=expense.date, item=expense.item, amount=expense.amount)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {"message": "success", "id": db_item.id}

@app.delete("/api/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.ExpenseModel).filter(models.ExpenseModel.id == expense_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(db_item)
    db.commit()
    return {"message": "deleted"}


# 3. メモ (Memos) API
@app.post("/api/memos")
def save_memo(memo: MemoSave, db: Session = Depends(get_db)):
    db_memo = db.query(models.MemoModel).filter(models.MemoModel.date == memo.date).first()
    if db_memo:
        db_memo.content = memo.content
    else:
        db_memo = models.MemoModel(date=memo.date, content=memo.content)
        db.add(db_memo)
    db.commit()
    return {"message": "success"}


# 4. チェックリスト (Checklists) API
@app.post("/api/checklists")
def add_checklist(item: CheckListCreate, db: Session = Depends(get_db)):
    db_item = models.CheckListModel(date=item.date, text=item.text, checked=False)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {"message": "success", "id": db_item.id}

@app.patch("/api/checklists/{checklist_id}")
def toggle_checklist(checklist_id: int, item: CheckListUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.CheckListModel).filter(models.CheckListModel.id == checklist_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    db_item.checked = item.checked
    db.commit()
    return {"message": "updated"}

@app.delete("/api/checklists/{checklist_id}")
def delete_checklist(checklist_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.CheckListModel).filter(models.CheckListModel.id == checklist_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Checklist item not found")
    db.delete(db_item)
    db.commit()
    return {"message": "deleted"}


# 5. 指定日付のデータ一括削除 API
@app.delete("/api/date/{date_str}")
def delete_date_data(date_str: str, db: Session = Depends(get_db)):
    db.query(models.ExpenseModel).filter(models.ExpenseModel.date == date_str).delete()
    db.query(models.MemoModel).filter(models.MemoModel.date == date_str).delete()
    db.query(models.CheckListModel).filter(models.CheckListModel.date == date_str).delete()
    db.commit()
    return {"message": f"All data for {date_str} deleted"}


# 6. 月間収支・予算 (Monthly Plans) API
@app.post("/api/monthly-plans")
def save_monthly_plan(plan: MonthlySavedata, db: Session = Depends(get_db)):
    db_plan = db.query(models.MonthlyPlanModel).filter(models.MonthlyPlanModel.month == plan.month).first()
    if db_plan:
        db_plan.income = plan.income
        db_plan.fixed = plan.fixed
        db_plan.budget = plan.budget
    else:
        db_plan = models.MonthlyPlanModel(
            month=plan.month,
            income=plan.income,
            fixed=plan.fixed,
            budget=plan.budget
        )
        db.add(db_plan)
    db.commit()
    return {"message": "success"}


# 7. 全般設定 (Config) API
@app.post("/api/config")
def save_config(config: MonthlyConfigSave, db: Session = Depends(get_db)):
    db_config = db.query(models.ConfigModel).first()
    if db_config:
        db_config.targetGoal = config.targetGoal
        db_config.dangerThreshold = config.dangerThreshold
        db_config.payday = config.payday
    else:
        db_config = models.ConfigModel(
            targetGoal=config.targetGoal,
            dangerThreshold=config.dangerThreshold,
            payday=config.payday
        )
        db.add(db_config)
    db.commit()
    return {"message": "success"}


# --- 静的ファイルのルーティング ---

@app.get("/calendar")
def read_index():
    index_file = BASE_DIR / "static" / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="static/index.html が見つかりません。")
    return FileResponse(index_file)

@app.get("/wolf")
def read_wolf():
    file_path = BASE_DIR / "static" / "wolf.html"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="static/wolf.html が見つかりません。")
    return FileResponse(file_path)

@app.get("/")
def read_login():
    login_file = BASE_DIR / "static" / "login.html"
    if not login_file.exists():
        raise HTTPException(status_code=404, detail="static/login.html が見つかりません。")
    return FileResponse(login_file)