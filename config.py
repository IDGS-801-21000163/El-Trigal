import os 
from sqlalchemy import create_engine

class Config(object):
    SECRET_KEY = "ClaveSecreta"
    SESSION_COOKIE_SECURE = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:root@127.0.0.1:3306/panaderia'
    SQLALCHEMY_TRACK_MODIFICATIONS = False