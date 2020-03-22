from flask import Blueprint
from flask_restful import Api
from config import Config
from .exceptions import custom_errors


class CustomApi(Api):
    def error_router(self, original_handler, e):
        if e.__str__()[:3] in Config.GLOBAL_ERROR_CODE:
            return original_handler(e)
        # 保证自定义的handler有机会工作

        if self._has_fr_route():
            try:
                return self.handle_error(e)
            except Exception:
                pass  # Fall through to original handler
        return original_handler(e)


v1 = Blueprint('v1', __name__)
api = CustomApi(v1, errors=custom_errors)


from . import users, errors
