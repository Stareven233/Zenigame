from . import api
from flask_restful import Resource, reqparse, fields, marshal
from ..models import Team, User
from flask import g, url_for
from .. import db
from .decorators import auth
from .exceptions import BadRequestError, ForbiddenError


user_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'avatar': fields.Url('main.get_avatar', attribute='avatar', absolute=True),
}


class UserItem(fields.Raw):
    def format(self, value):
        return marshal(value, user_fields)


class JoinUrl(fields.Url):
    def output(self, key, obj):
        value = getattr(obj, key if self.attribute is None else self.attribute)
        return url_for(self.endpoint, _external=self.absolute, inv=value)


team_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'desc': fields.String,
    'leader_id': fields.Integer(attribute='leader'),
    'check_s': fields.Integer,
    'check_e': fields.Integer,
    'members': fields.List(UserItem, attribute='users'),
    'inv_url': JoinUrl('v1.join_team', attribute='inv_code', absolute=True)
}


def time_check(check_s, check_e):
    """二者间有大小关系，不可直接 flask_restful.inputs.int_range """
    if check_s < 0 or check_e < 0:
        raise BadRequestError('打卡时间不可为负值')
    if check_s >= 24*60*60 or check_e >= 86400:
        raise BadRequestError('打卡时间必须在一天(24*60*60s)以内')
    if check_s >= check_e:
        raise BadRequestError('打卡开始时间须小于截止时间')


class TeamListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqpost = reqparse.RequestParser()
        self.reqpost.add_argument('name', type=str, required=True, location='json')
        self.reqpost.add_argument('desc', type=str, required=False, location='json')
        self.reqpost.add_argument('check_s', type=int, required=True, location='json')
        self.reqpost.add_argument('check_e', type=int, required=True, location='json')
        super().__init__()

    def post(self):
        """登录用户创建一个团队"""
        args = self.reqpost.parse_args(strict=True)
        time_check(args['check_s'], args['check_e'])

        team = Team(**args)
        user = g.current_user
        team.users.append(user)

        team.leader = user.id
        team.renew_inv_code()
        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(team, team_fields)}
        return response, 201


class TeamAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('action', type=int, required=True, location='json')
        self.reqparse.add_argument('uid', type=int, required=True, location='json')
        self.reqpatch = reqparse.RequestParser()
        self.reqpatch.add_argument('name', type=str, required=False, location='json')
        self.reqpatch.add_argument('desc', type=str, required=False, location='json')
        self.reqpatch.add_argument('check_s', type=int, required=False, location='json')
        self.reqpatch.add_argument('check_e', type=int, required=False, location='json')
        super().__init__()

    def post(self, tid):
        """对某个团队队长主动拉人/踢人 他人退出 及队长职位转让
        action: 1-加入 2-退出 3-转移职务
        uid: 被操作者，允许操作自己
        注意：加入只能由队长拉入或通过邀请码，不能直接加入
        """
        args = self.reqparse.parse_args(strict=True)
        action, uid = args['action'], args['uid']

        team = Team.query.get_or_404(tid)
        operator = g.current_user
        user = User.query.get_or_404(uid)

        op_admin = operator.id == team.leader
        op_self = operator.id == user.id

        if op_admin and op_self:  # 队长操作自己
            raise BadRequestError('队长不可加入/退出，请先转交队长职位')

        if op_admin or op_self:  # 队长操作他人 / 他人操作自己
            joined = bool(team.users.filter_by(id=user.id).first())  # 是否已加入该团队

            if action == 1 and op_admin and not joined:
                team.users.append(user)
            elif action == 2 and joined:
                team.users.remove(user)
            elif action == 3 and joined:
                team.leader = user.id  # 队长仅由team.leader标识
            else:
                raise BadRequestError('请求无效或不满足执行条件')

            db.session.add(team)
            db.session.commit()
        else:
            raise BadRequestError('不可操作其他团队成员')

        response = {'code': 0, 'message': ''}
        return response, 200

    def patch(self, tid):
        args = self.reqpatch.parse_args(strict=True)
        team = Team.query.get_or_404(tid)
        operator = g.current_user

        if operator.id != team.leader:
            raise BadRequestError('仅队长可修改团队信息')

        check_s, check_e = args.check_s, args.check_e
        if check_s and check_e:
            time_check(check_s, check_e)
        elif check_s:
            time_check(check_s, team.check_e)
        elif check_e:
            time_check(team.check_s, check_e)

        team.alter(args)
        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200

    def delete(self, tid):
        team = Team.query.get_or_404(tid)
        operator = g.current_user
        if operator.id != team.leader:
            raise BadRequestError('仅队长可解散团队')
        db.session.delete(team)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200

    def get(self, tid):
        team = Team.query.get_or_404(tid)
        if not team.users.filter_by(id=g.current_user.id).first():
            raise ForbiddenError('仅成员可查看团队信息')

        response = {'code': 0, 'message': '', 'data': marshal(team, team_fields)}
        return response, 200


class TeamJoinAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('inv', type=str, required=True, location=['args', 'json'])
        super().__init__()

    def get(self):
        args = self.reqparse.parse_args(strict=True)
        team = Team.query.filter_by(inv_code=args.inv).first()

        if team is None:
            raise BadRequestError('邀请码错误或过期')

        if not team.users.filter_by(id=g.current_user.id).first():
            team.users.append(g.current_user)

        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200

    def put(self):
        args = self.reqparse.parse_args(strict=True)
        team = Team.query.filter_by(inv_code=args.inv).first()

        if team is None:
            raise BadRequestError('邀请码错误或过期')

        if team.leader != g.current_user.id:
            raise ForbiddenError('仅队长可更新邀请码')

        team.renew_inv_code()
        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(team, team_fields)}
        return response, 200


api.add_resource(TeamListAPI, '/teams', endpoint='teams')
api.add_resource(TeamAPI, '/teams/<int:tid>', endpoint='team')
api.add_resource(TeamJoinAPI, '/teams/join', endpoint='join_team')
