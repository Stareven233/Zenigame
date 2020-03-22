from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from ..models import User
from flask import g

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)


@basic_auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    # 至少获取令牌是需要验证密码
    if not user or not user.verify_password(password):
        return False
    g.current_user = user
    return True


@token_auth.verify_token
def verify_token(token):
    user = User.verify_auth_token(token)
    if not user:
        return False
    g.current_user = user
    return True
