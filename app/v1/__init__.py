from flask import Blueprint
from flask_restful import Api
from .exceptions import MyApiError
from config import GLOBAL_ERROR_CODE


class CustomApi(Api):
    def error_router(self, original_handler, e):
        # 保证errors.py里的处理器会被使用
        check = (e.__str__()[:3] not in GLOBAL_ERROR_CODE) or isinstance(e, MyApiError)
        if self._has_fr_route() and check:
            try:
                return self.handle_error(e)
            except Exception:
                pass
        return original_handler(e)


v1 = Blueprint('v1', __name__)
api = Api(v1)
# api = Api(v1, errors=custom_errors) 不够灵活


from . import users, teams, errors
from . import schedules, attendances, tasks, questionnaires, logs
