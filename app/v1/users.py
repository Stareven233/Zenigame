from . import api
from flask_restful import Resource, reqparse, fields, marshal
from ..models import User
from flask import current_app, g, send_from_directory, url_for
from .. import db
from .decorators import auth
import copy
from .exceptions import UserAlreadyExistsError, IncorrectPasswordError
from werkzeug.datastructures import FileStorage
from .. import up_files
from os import remove
from flask_uploads import extension

user_fields = {
    'id': fields.Integer,
    'username': fields.String,
    'name': fields.String,
    'avatar': fields.Url('v1.avatar', absolute=True),
    'team_id': fields.List(fields.Integer, attribute='teams', default=[])  # 让team通过__repr__打印
}
response_template = {'code': 0, 'message': "", 'data': {}}


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
            raise UserAlreadyExistsError(1001, '用户已存在')
        user = User(username=username, name=name)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        response = copy.deepcopy(response_template)
        response['data'] = marshal(user, user_fields)
        return response, 201


class TokenAPI(Resource):
    decorators = [auth.login_required]

    def get(self):
        # 双令牌无感知刷新
        access_token = g.current_user.generate_auth_token(expiration=24*60*60)
        refresh_token = g.current_user.generate_auth_token(expiration=30*24*3600)
        response = copy.deepcopy(response_template)
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
        response = copy.deepcopy(response_template)
        response['data'] = marshal(user, user_fields)
        return response, 200

    def patch(self):
        self.reqparse.add_argument('name', type=str, required=True, location='json')
        args = self.reqparse.parse_args()
        user = g.current_user
        user.name = args['name']
        db.session.add(user)
        db.session.commit()
        response = copy.deepcopy(response_template)
        response['data'] = marshal(user, user_fields)
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
            raise IncorrectPasswordError(1003, '无效密码')
        user.hash_password(args['password2'])
        db.session.add(user)
        db.session.commit()
        response = copy.deepcopy(response_template)
        response['data'] = marshal(user, user_fields)
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
        avatar = args['avatar']
        ext = extension(avatar.filename)

        if user.avatar:
            remove(current_app.config['UPLOADED_FILES_DEST'] + 'avatar/' + f'{user.id}.{user.avatar}')

        up_files.save(avatar, name=f'avatar/{user.id}.{ext}')
        user.avatar = ext
        db.session.add(user)
        db.session.commit()
        response = copy.deepcopy(response_template)
        response['data']['avatar'] = url_for('v1.avatar', id=user.id, _external=True)
        return response, 200


class UserAvatarAPI(Resource):
    def get(self, id):
        user = User.query.get_or_404(id)
        return send_from_directory(current_app.config['UPLOADED_FILES_DEST'],
                                   f'avatar/{id}.{user.avatar}', as_attachment=False)


api.add_resource(RegisterAPI, '/users/register', endpoint='register')
api.add_resource(TokenAPI, '/users/token', endpoint='token')
api.add_resource(UserListAPI, '/users', endpoint='users')
api.add_resource(UserPwdAPI, '/users/password', endpoint='password')
api.add_resource(UserAvatarsAPI, '/users/avatar', endpoint='avatars')
api.add_resource(UserAvatarAPI, '/users/<int:id>/avatar', endpoint='avatar')
