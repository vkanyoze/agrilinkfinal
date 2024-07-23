from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
import pymysql
pymysql.install_as_MySQLdb()
db = SQLAlchemy()  

jwt = JWTManager()
