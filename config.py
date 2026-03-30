class DevelopmentConfig:
    SECRET_KEY = 'devkey'

    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:1234@localhost/panaderia"
    SQLALCHEMY_TRACK_MODIFICATIONS = False