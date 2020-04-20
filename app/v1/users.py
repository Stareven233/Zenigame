from . import api
from flask_restful import Resource, reqparse, fields, marshal
from ..models import User
from flask import g, send_from_directory, url_for
from .. import db, up_files
from .decorators import auth
from .exceptions import UserAlreadyExistsError, IncorrectPasswordError
from werkzeug.datastructures import FileStorage
from os import remove
from flask_uploads import extension
from config import Config, DEFAULT_AVATAR

user_fields = {
    'id': fields.Integer,
    'username': fields.String,
    'name': fields.String,
    'avatar': fields.Url('v1.avatar', attribute='avatar', absolute=True),
    'team_id': fields.List(fields.Integer, attribute='teams', default=[])  # 让team通过__repr__打印
}


class RegisterAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('username', type=str, required=True, help='用户名不能为空', location='json')
        self.reqparse.add_argument('password', type=str, required=True, help='密码不能为空', location='json')
        self.reqparse.add_argument('name', type=str, required=False, help='不填则默认为username', location='json')
        super().__init__()

    def post(self):
        args = self.reqparse.parse_args()  # 返回Namespace，行为类似字典
        username = args['username']
        password = args['password']
        name = args['name'] or username
        if User.query.filter_by(username=username).first():
            raise UserAlreadyExistsError()

        user = User(username=username, name=name)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': marshal(user, user_fields)}
        return response, 201


class TokenAPI(Resource):
    decorators = [auth.login_required]

    def get(self):
        # 双令牌无感知刷新
        access_token = g.current_user.generate_auth_token(expiration=24*60*60)
        refresh_token = g.current_user.generate_auth_token(expiration=30*24*3600)

        response = {'code': 0, 'msg': '', 'data': {}}
        response['data']['access_token'] = access_token.decode('ascii')
        response['data']['refresh_token'] = refresh_token.decode('ascii')
        return response, 200


class UserListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super().__init__()

    def get(self):  # 依据id/username查询用户，或返回当前用户
        self.reqparse.add_argument('id', type=int, required=False, location=['json', 'args'])
        self.reqparse.add_argument('username', type=str, required=False, location=['json', 'args'])
        args = self.reqparse.parse_args()

        user = User.query.get(args['id'])
        user = user or User.query.filter_by(username=args['username']).first()
        user = user or g.current_user

        response = {'code': 0, 'msg': '', 'data': marshal(user, user_fields)}
        return response, 200

    def patch(self):
        self.reqparse.add_argument('name', type=str, required=True, location='json')
        args = self.reqparse.parse_args()

        user = g.current_user
        user.name = args['name']
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': marshal(user, user_fields)}
        return response, 200


class UserPwdAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('password', type=str, required=True, help='密码不能为空', location='json')
        self.reqparse.add_argument('password2', type=str, required=True, help='新密码不能为空', location='json')
        super().__init__()

    def put(self):
        args = self.reqparse.parse_args()
        user = g.current_user
        if not user.verify_password(args['password']):
            raise IncorrectPasswordError()

        user.hash_password(args['password2'])
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': marshal(user, user_fields)}
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
        args = self.reqparse.parse_args()
        f_name = user.avatar

        if f_name and f_name != DEFAULT_AVATAR:
            remove(Config.UPLOADED_FILES_DEST + f'avatar/{f_name}')

        avatar = args['avatar']
        ext = extension(avatar.filename)
        f_name = f'{user.id}.{ext}'
        up_files.save(avatar, name=f'avatar/{f_name}')

        user.avatar = f_name
        db.session.add(user)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': url_for('v1.avatar', avatar=user.avatar, _external=True)}
        return response, 200


class UserAvatarAPI(Resource):
    def get(self, avatar):
        return send_from_directory(Config.UPLOADED_FILES_DEST, f'avatar/{avatar}')


api.add_resource(RegisterAPI, '/users/register', endpoint='register')
api.add_resource(TokenAPI, '/users/token', endpoint='token')
api.add_resource(UserListAPI, '/users', endpoint='users')
api.add_resource(UserPwdAPI, '/users/password', endpoint='password')
api.add_resource(UserAvatarsAPI, '/users/avatar', endpoint='avatars')
api.add_resource(UserAvatarAPI, '/users/<string:avatar>', endpoint='avatar')
