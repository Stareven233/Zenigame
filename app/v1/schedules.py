from . import api
from flask_restful import Resource, reqparse, inputs, marshal, fields
from ..models import Schedule, Team
from .. import db
from flask import g
from .exceptions import ForbiddenError

schedule_fields = {
    'id': fields.Integer,
    'desc': fields.String,
    'start': fields.DateTime(dt_format='iso8601'),
    'end': fields.DateTime(dt_format='iso8601'),
    'team_id': fields.String,
}


class ScheduleList(Resource):
    def __init__(self):
        self.reqparser = reqparse.RequestParser()
        self.reqparser.add_argument('desc', type=str, required=True, location='json')
        self.reqparser.add_argument('urgency', type=inputs.int_range(1, 3), required=True, location='json')
        # urgency是紧急程度，分三级
        self.reqparser.add_argument('span', type=inputs.iso8601interval, required=True, location='json')
        # span指日期跨度，解析类似 2013-01-01/2013-02-28 的字符串

    def post(self, tid):
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


api.add_resource(ScheduleList, '/teams/<int:tid>/schedules')
