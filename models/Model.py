# 模型文件

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index, CHAR, VARCHAR
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
Base = declarative_base()
engine = create_engine("mysql+pymysql://root:hwq6686043@localhost:3306/test")
# engine = create_engine("mysql+pymysql://ops_platform:0OqQZdPVmR5PjaBdz7hT@10.9.123.228:3306/ops_platform?charset=utf8mb4")
Session = sessionmaker(bind=engine)
session_model = Session()


class User(Base):

    __tablename__ = 'user_test'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(VARCHAR(32), nullable=False)
    password = Column(VARCHAR(32), nullable=False)
    phone = Column(VARCHAR(20), nullable=False)

    def __init__(self, dic_data):
        self.id = dic_data['id']
        self.account = dic_data['account']
        self.password = dic_data['password']
        self.phone = dic_data['phone']
