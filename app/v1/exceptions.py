from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response
from .. import compact_dumps


class MyApiError(HTTPException):
    e_code = 0

    def __init__(self, description=None):
        super().__init__(description)
        resp = Response(response=self.to_json(), status=self.code, mimetype='application/json')
        self.response = resp

    def to_json(self):
        response = {'code': self.e_code, 'message': self.description}
        return compact_dumps(response)


class ForbiddenError(MyApiError):
    code = 403
    description = '禁止访问该资源'
    e_code = 1001


class NotFound(MyApiError):
    code = 404
    description = '请求资源不存在'
    e_code = 2001


class BadRequestError(MyApiError):
    code = 400
    description = '请检查请求参数是否正确'
    e_code = 2002


class UserAlreadyExistsError(MyApiError):
    code = 409
    description = '该用户已存在'
    e_code = 1101


class IncorrectPasswordError(MyApiError):
    code = 401
    description = '密码错误，认证无效'
    e_code = 1102
