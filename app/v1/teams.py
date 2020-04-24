from . import api
from flask_restful import Resource, reqparse, fields, marshal
from ..models import Team, User
from flask import g
from .. import db
from .decorators import auth
from .exceptions import BadRequestError

team_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'desc': fields.String,
    'check_s': fields.Integer,
    'check_e': fields.Integer,
}


# def time24(t_str):
#     match = re.fullmatch(r'(\d{2}):(\d{2}):(\d{2})', t_str, re.A)
#     if match is None:
#         raise TypeError("must be a string like: 'hh:mm:ss'")
#     h, m, s = tuple(map(int, match.groups()))
#     if h > 23 or m > 59 or s > 59:
#         raise TypeError("must be a legal 24-hour system time string")
#     return t_str


def time_check(check_s, check_e):
    if check_s < 0 or check_e < 0:
        raise BadRequestError('打卡时间不可为负值')
    if check_s >= 24*60*60 or check_e >= 86400:
        raise BadRequestError('打卡时间必须在24*60*60以内')
    if check_s >= check_e:
        raise BadRequestError('打卡起始时间须小于结束时间')


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
        args = self.reqpost.parse_args(strict=True)
        time_check(args['check_s'], args['check_e'])

        team = Team(**args)
        user = g.current_user
        team.users.append(user)
        team.leader = user.id
        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': marshal(team, team_fields)}
        return response, 200


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
        args = self.reqparse.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        operator = g.current_user
        action, uid = args['action'], args['uid']
        user = User.query.get_or_404(uid)
        if operator.id == team.leader and operator.id == user.id:
            raise BadRequestError('团长不可操作自己(加入/退出)，请先转交团长职位')
        time_check(args['check_s'], args['check_e'])

        if operator.id == team.leader or operator.id == user.id:
            joined = bool(team.users.filter_by(id=user.id).first())
            if action == 1 and not joined:  # action: 1-加入 2-退出 3-转移职务
                team.users.append(user)
            elif action == 2 and joined:
                team.users.remove(user)
            elif action == 3 and joined:
                team.leader = user.id  # 团长仅由team.leader标识
            else:
                raise BadRequestError('请求无效或不满足执行条件')

            db.session.add(team)
            db.session.commit()
        else:
            raise BadRequestError('不可操作其他团队成员')

        response = {'code': 0, 'msg': '', 'data': marshal(team, team_fields)}
        return response, 200

    def patch(self, tid):
        args = self.reqpatch.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        operator = g.current_user
        if operator.id != team.leader:
            raise BadRequestError('仅团长可修改团队信息')
        team.alter(args)
        db.session.add(team)
        db.session.commit()

        response = {'code': 0, 'msg': '', 'data': marshal(team, team_fields)}
        return response, 200

    def delete(self, tid):
        team = Team.query.get_or_404(tid)
        operator = g.current_user
        if operator.id != team.leader:
            raise BadRequestError('仅团长可解散团队')
        db.session.delete(team)
        db.session.commit()

        response = {'code': 0, 'msg': ''}
        return response, 200

    def get(self, tid):
        team = Team.query.get_or_404(tid)
        response = {'code': 0, 'msg': '', 'data': marshal(team, team_fields)}
        return response, 200


api.add_resource(TeamListAPI, '/teams', endpoint='teams')
api.add_resource(TeamAPI, '/teams/<int:tid>', endpoint='team')
