from flask import g
from flask_restful import Resource, reqparse, marshal, fields

from . import api
from ..models import Team, Log
from .. import db
from .decorators import auth
from .exceptions import ForbiddenError

from config import LOG_PER_PAGE


log_fields = {
    'uid': fields.Integer,
    'desc': fields.String,
    'datetime': fields.DateTime(dt_format='iso8601'),
}
reqparser = reqparse.RequestParser()
reqparser.add_argument('page', type=int, default=1, location='args')


class LogListAPI(Resource):
    decorators = [auth.login_required]

    def get(self, tid):
        args = reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的日志')

        pagination = team.logs.order_by(Log.datetime.desc()).paginate(
            page=args.page,
            per_page=LOG_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'logs': marshal(pagination.items, log_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


api.add_resource(LogListAPI, '/teams/<int:tid>/logs')
