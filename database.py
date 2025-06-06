from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


URL_DATABASE = 'postgresql://admin:rIC04df53bd5jFSHgYjMcIF2xI2ZkF2C@dpg-d11hm6vfte5s739892qg-a.oregon-postgres.render.com/et_ntiz'

engine = create_engine(URL_DATABASE)

sessionLocal = sessionmaker(autocommit=False, autoflush=False , bind=engine)

Base = declarative_base( )