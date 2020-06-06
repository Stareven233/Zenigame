from os import getenv
from os.path import dirname, sep


GLOBAL_ERROR_CODE = '400 401 403 404 500'.split()
MSG_PER_PAGE = 10
DEFAULT_AVATAR = '0.jpg'
ALLOWED_IMG_EXT = 'jpg jpeg png'.split()


class Config(object):
    SECRET_KEY = 'M<JZ7]6P-r_C0C3hNzY#gbOjY'
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://root:{getenv("DATABASE_PW")}@localhost:3306/Zenigame'
    # SQLALCHEMY_DATABASE_URI = f'mysql+mysqlconnector://root:{getenv("DATABASE_PW")}@localhost:3306/Zenigame'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOADED_FILES_DEST = dirname(__file__)+sep+'app'+sep+'static'+sep
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024
