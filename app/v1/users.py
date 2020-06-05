from . import api, v1
from flask_restful import Resource, reqparse, fields, marshal, inputs
from ..models import User
from flask import g, url_for
from .. import db, up_files
from .decorators import auth
from .exceptions import UserAlreadyExistsError, IncorrectPasswordError
from werkzeug.datastructures import FileStorage
from os import remove
from flask_uploads import extension
from config import Config, DEFAULT_AVATAR
from uuid import uuid3, NAMESPACE_URL


class TeamItem(fields.Raw):
    def format(self, value):
        return value.tid


user_fields = {
    'id': fields.Integer,
    'username': fields.String,
    'name': fields.String,
    'avatar': fields.Url('main.get_avatar', attribute='avatar', absolute=True),
    'email': fields.String,
    'team_id': fields.List(TeamItem, attribute='teams')  # , default=[]
}


class TokenAPI(Resource):
    decorators = [auth.login_required]

    def get(self):
        # 双令牌无感知刷新
        access_token = g.current_user.generate_auth_token(expiration=24*60*60)
        refresh_token = g.current_user.generate_auth_token(expiration=30*24*3600)

        response = {'code': 0, 'message': '', 'data': {}}
        response['data']['access_token'] = access_token.decode('ascii')
        response['data']['refresh_token'] = refresh_token.decode('ascii')
        return response, 200


class UserListAPI(Resource):
    method_decorators = {'get': [auth.login_required], 'patch': [auth.login_required]}

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super().__init__()

    def get(self):  # 依据id/username查询用户，或返回当前用户
        self.reqparse.add_argument('id', type=int, required=False, location=['json', 'args'])
        self.reqparse.add_argument('username', type=str, required=False, location=['json', 'args'])
        args = self.reqparse.parse_args(strict=True)

        user = User.query.get(args.id)
        user = user or User.query.filter_by(username=args['username']).first()

        if not user:
            user = User(avatar=DEFAULT_AVATAR) if args.id else g.current_user
        # user = user or g.current_user

        response = {'code': 0, 'message': '', 'data': marshal(user, user_fields)}
        return response, 200

    def post(self):
        email_t = inputs.regex(r'^[0-9a-zA-Z_-]+@[0-9a-zA-Z_-]+(?:.[0-9a-zA-Z_-]+){1,2}$')
        username_t = inputs.regex(r'^[0-9a-zA-Z\u4e00-\u9fa5]{2,16}$')  # 不能跟email混淆

        self.reqparse.add_argument('email', type=email_t, required=True, help='为空或不合法', location='json')
        self.reqparse.add_argument('username', type=username_t, required=True, help='为空或不合法', location='json')
        self.reqparse.add_argument('password', type=str, required=True, help='密码不能为空', location='json')
        self.reqparse.add_argument('name', type=str, required=False, help='不填则默认为username', location='json')
        args = self.reqparse.parse_args(strict=True)

        email = args.email
        username = args['username']
        password = args['password']
        name = args['name'] or username

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            raise UserAlreadyExistsError()

        user = User(email=email, username=username, name=name)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(user, user_fields)}
        return response, 201

    def patch(self):  # 登录即可确认身份，故不需id
        """修改用户名"""
        email_t = inputs.regex(r'^[0-9a-zA-Z_-]+@[0-9a-zA-Z_-]+(?:.[0-9a-zA-Z_-]+){1,2}$')
        self.reqparse.add_argument('name', type=str, required=False, location='json')
        self.reqparse.add_argument('email', type=email_t, required=False, location='json')
        args = self.reqparse.parse_args(strict=True)

        user = g.current_user
        user.alter(args)
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(user, user_fields)}
        return response, 200


class UserPwdAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('password', type=str, required=True, help='密码不能为空', location='json')
        self.reqparse.add_argument('password2', type=str, required=True, help='新密码不能为空', location='json')
        super().__init__()

    def put(self):
        args = self.reqparse.parse_args(strict=True)
        user = g.current_user
        if not user.verify_password(args['password']):
            raise IncorrectPasswordError()

        user.hash_password(args['password2'])
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(user, user_fields)}
        return response, 200


class UserAvatarsAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('avatar', type=FileStorage, required=True, location='files')
        # self.reqparse.add_argument('Content-Length', type=int, required=False, location='headers')
        super().__init__()

    def put(self):
        user = g.current_user
        args = self.reqparse.parse_args(strict=True)
        f_name = user.avatar

        if f_name and f_name != DEFAULT_AVATAR:
            remove(Config.UPLOADED_FILES_DEST + f'img/{f_name}')

        avatar = args['avatar']
        ext = extension(avatar.filename)

        if f_name == DEFAULT_AVATAR:  # 节约计算，但username不能再变
            f_name = uuid3(NAMESPACE_URL, user.username).hex.replace('-', '')
            f_name = f'{f_name}.{ext}'
        else:
            f_name = f_name[:-3] + ext

        up_files.save(avatar, name=f'img/{f_name}')
        user.avatar = f_name
        db.session.add(user)
        db.session.commit()

        avatar = url_for('main.get_avatar', avatar=user.avatar, _external=True)
        response = {'code': 0, 'message': '', 'data': {'avatar': avatar}}
        return response, 200


api.add_resource(TokenAPI, '/users/token', endpoint='token')
api.add_resource(UserListAPI, '/users', endpoint='users')
api.add_resource(UserPwdAPI, '/users/password', endpoint='password')
api.add_resource(UserAvatarsAPI, '/users/avatar', endpoint='avatars')
