from flask import g
from flask_restful import Resource, reqparse, inputs, marshal, fields

from . import api
from ..models import Attendance, Team
from .. import db
from .decorators import auth
from .exceptions import ForbiddenError

from datetime import datetime
from sqlalchemy import extract


attendance_fields = {
    # 'id': fields.Integer,  # 打卡记录不能改，也不能删，不需要id
    'uid': fields.Integer,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'punctual': fields.Boolean,
    'tid': fields.Integer(attribute='team_id'),
}


class AttendanceListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def post(self, tid):
        """团队成员在规定时间内打卡"""

        team = Team.query.get_or_404(tid)
        user = g.current_user
        d = datetime.now()

        if not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('仅本团队成员可打卡')

        if team.attendances.filter(
                Attendance.uid == user.id,
                extract('year', Attendance.datetime) == d.year,
                extract('month', Attendance.datetime) == d.month,
                extract('day', Attendance.datetime) == d.day,
        ).first():
            raise ForbiddenError('不可重复打卡')

        if not (team.check_s <= d.time()):
            raise ForbiddenError('未到打卡时间')

        a = Attendance(uid=user.id, datetime=d)
        a.punctual = d.time() <= team.check_e
        team.attendances.append(a)

        db.session.add_all([a, team])
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(a, attendance_fields)}
        return response, 201

    def get(self, tid):
        """
        管理员通过spec参数查看打卡详细信息，其他只有统计数据
        :param tid: 查询的团队id
        :return: 返回某一天的打卡数据
        """
        self.reqparser.add_argument('date', type=inputs.date, required=True, location='args')
        self.reqparser.add_argument('spec', type=inputs.boolean, default=False, location='args')
        # 是否返回详细信息(仅对队长有效)
        self.reqparser.add_argument('self', type=inputs.boolean, default=False, location='args')
        # 是否返回自己的详细信息(覆盖spec)
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可获取其他团队的打卡记录')

        date_tuple = args.date.timetuple()[:3]
        dt_s = datetime(*date_tuple)  # 一天的开端
        dt_e = datetime.max.replace(*date_tuple)  # 一天的结尾

        query = team.attendances.filter(Attendance.datetime.between(dt_s, dt_e))

        if args.self:
            # 用户查看自己的打卡情况
            a = query.filter(Attendance.uid == user.id).first()
            data = marshal(a, attendance_fields) if a is not None else {}

        elif args.spec and user.id == team.leader:
            # 队长查看全团队详情
            data = [marshal(a, attendance_fields) for a in query]

        else:
            # 一般成员查看团队简要信息: 已打卡与准时的人数
            punctual = query.filter_by(punctual=True).count()
            data = {'present': query.count(), 'punctual': punctual}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


api.add_resource(AttendanceListAPI, '/teams/<int:tid>/attendances')
