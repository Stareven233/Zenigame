from . import v1
from .decorators import basic_auth, token_auth

response = {'code': 0, 'message': ""}


@basic_auth.error_handler
def unauthorized():
    response['code'] = 1000
    response['message'] = "认证失败"
    return response, 403


@token_auth.error_handler
def token_expired():
    response['code'] = 1000
    response['message'] = "认证失败"
    return response, 403


@v1.app_errorhandler(401)
def authorize_failed(e):
    # Flask_RESTful Api 传的参数，exception类型
    response['code'] = 1000
    response['message'] = "认证失败"
    return response, 403
# 认证的统一以403代替401，防止浏览器弹验证窗口


@v1.app_errorhandler(403)
def forbidden(e):
    response['code'] = 1001
    response['message'] = "禁止访问"
    return response, 403


@v1.app_errorhandler(404)
def not_found(e):
    response['code'] = 2001
    response['message'] = "资源不存在"
    return response, 404


@v1.app_errorhandler(400)
def bad_request(e):
    response['code'] = 2002
    response['message'] = "请检查请求参数是否正确"
    return response, 400


@v1.app_errorhandler(500)
def server_error(e):
    response['code'] = 3001
    response['message'] = "服务器错误"
    return response, 500
