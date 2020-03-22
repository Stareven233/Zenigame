custom_errors = {
    'UserAlreadyExistsError': {
        'code': 1001,
        'message': '用户名重复，该用户已存在',
        'status': 409
    },
    'IncorrectPasswordError': {
        'code': 1003,
        'message': '密码错误，认证无效',
        'status': 401
    },
    'UploadNotAllowed': {
        'code': 2003,
        'message': '无效的上传文件',
        'status': 422
    }
}


class AuthException(Exception):
    def __init__(self, code=1000, message='认证无效', *args):
        self.args = args
        self.code = code
        self.message = message


class UserAlreadyExistsError(AuthException):
    pass


class IncorrectPasswordError(AuthException):
    pass
