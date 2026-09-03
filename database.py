"""
database.py
負責人: 梁偉航

統一管理 SQLAlchemy 引擎與 Session 工廠。
main.py 與 db_client.py 共用同一個 engine,避免重複建立連線。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models3

DATABASE_URL = "sqlite:///./la3_plantquest3.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
models3.Base.metadata.create_all(bind=engine)
