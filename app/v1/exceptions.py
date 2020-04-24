from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import BaseResponse
from .. import compact_dumps


class MyApiError(HTTPException):
    e_code = 0

    def __init__(self, description=None):
        super().__init__(description)
        resp = BaseResponse(response=self.to_json(), status=self.code, mimetype='application/json')
        self.response = resp

    def to_json(self):
        response = {'code': self.e_code, 'msg': self.description}
        return compact_dumps(response)


class UserAlreadyExistsError(MyApiError):
    code = 409
    description = '该用户已存在'
    e_code = 1101


class IncorrectPasswordError(MyApiError):
    code = 401
    description = '密码错误，认证无效'
    e_code = 1102


class BadRequestError(MyApiError):
    code = 400
    description = '请检查请求参数是否正确'
    e_code = 2002
