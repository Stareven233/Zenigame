from flask import Flask
from config import Config, ALLOWED_IMG_EXT
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads
from json import dumps
from functools import partial

json_config = {'ensure_ascii': False, 'indent': None, 'separators': (',', ':')}
compact_dumps = partial(dumps, **json_config)


class CustomUpSet(UploadSet):
    def resolve_conflict(self, target_folder, basename):
        return basename  # 保存同名文件时直接覆盖


db = SQLAlchemy()
up_files = CustomUpSet(name='FILES', extensions=ALLOWED_IMG_EXT)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    configure_uploads(app, up_files)
    from .v1 import v1  # 不能在db初始化前，因为v1有用到db
    app.register_blueprint(v1, url_prefix='/v1')
    from .main import main
    app.register_blueprint(main, url_prefix='/')
    return app


def create_db_table(app):
    with app.app_context():
        db.create_all()


# from app import db
# from app.models import User
# def update_db():
#     with app.app_context():
#         users = User.query.all()
#         for u in users:
#             u.hash_password(u.username)
#             db.session.add(u)
#         db.session.commit()
