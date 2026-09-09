import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 環境変数から DATABASE_URL を取得
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# SupabaseやVercel Postgresなどの `postgres://` を `postgresql://` に自動変換（SQLAlchemy対策）
if SQLALCHEMY_DATABASE_URL and SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 環境変数が設定されていない場合に明確にエラーを出す
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("環境変数 'DATABASE_URL' が設定されていません。VercelのEnvironment Variablesを確認してください。")

# クラウドDB用に engine を作成（SQLite用の check_same_thread オプションは削除）
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()