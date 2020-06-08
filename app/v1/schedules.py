from . import api
from flask_restful import Resource, reqparse, inputs, marshal, fields
from ..models import Schedule, Team
from .. import db
from flask import g
from .decorators import auth
from .exceptions import ForbiddenError
from datetime import date as Date
from sqlalchemy import not_, or_


schedule_fields = {
    'id': fields.Integer,
    'desc': fields.String,
    'urgency': fields.Integer,
    'start': fields.DateTime(dt_format='iso8601'),
    'end': fields.DateTime(dt_format='iso8601'),
    # 'team_id': fields.String,  # 反正只能取本团队的，该字段无意义
}


class ScheduleListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def post(self, tid):
        self.reqparser.add_argument('desc', type=str, required=True, location='json')
        self.reqparser.add_argument('urgency', type=inputs.int_range(1, 3), required=True, location='json')
        # urgency是紧急程度，分三级
        self.reqparser.add_argument('start', type=inputs.date, required=True, location='json')
        self.reqparser.add_argument('end', type=inputs.date, required=True, location='json')
        # 该日程的时期跨度，格式：2020-03-01 的字符串
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if user.id != team.leader:
            raise ForbiddenError('仅队长可创建日程')

        s = Schedule(**args)
        team.schedules.append(s)

        db.session.add_all([s, team])
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(s, schedule_fields)}
        return response, 201

    def get(self, tid):
        self.reqparser.add_argument('year', type=int, required=True, location='args')
        self.reqparser.add_argument('month', type=inputs.int_range(1, 12), required=True, location='args')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        if not team.users.filter_by(id=g.current_user.id).first():
            raise ForbiddenError('不可获取其他团队的日程')

        y, m = args.year, args.month
        days_of_month = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        start = Date(y, m, 1)
        end = Date(y, m, days_of_month[m])
        # end = start.replace(year=y + (m is 12), month=(m is 12) or m+1) - Date.resolution
        # 所求月第一天与最后一天

        schedules = Schedule.query.filter(not_(or_(Schedule.start > end, Schedule.end < start)))
        # 筛选出日期跨度与该月有交集的所有日程
        data = [marshal(s, schedule_fields) for s in schedules]

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


class ScheduleAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def patch(self, sid):
        self.reqparser.add_argument('desc', type=str, required=False, location='json')
        self.reqparser.add_argument('urgency', type=inputs.int_range(1, 3), required=False, location='json')
        self.reqparser.add_argument('start', type=inputs.date, required=False, location='json')
        self.reqparser.add_argument('end', type=inputs.date, required=False, location='json')
        args = self.reqparser.parse_args(strict=True)

        schedule = Schedule.query.get_or_404(sid)
        if g.current_user.id != schedule.team.leader:
            raise ForbiddenError('仅队长可修改日程')

        if args.urgency:
            args.urgency = str(args.urgency)
        schedule.alter(args)

        db.session.add(schedule)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200

    def delete(self, sid):
        schedule = Schedule.query.get_or_404(sid)
        if g.current_user.id != schedule.team.leader:
            raise ForbiddenError('仅队长可删除日程')

        db.session.delete(schedule)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200


api.add_resource(ScheduleListAPI, '/teams/<int:tid>/schedules')
api.add_resource(ScheduleAPI, '/schedules/<int:sid>')
