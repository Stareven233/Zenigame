from . import api
from flask_restful import Resource, reqparse, inputs, marshal, fields
from ..models import Team, Task, Archive
from .. import db
from flask import g
from .decorators import auth
from .exceptions import ForbiddenError
from config import TASK_PER_PAGE
from werkzeug.datastructures import FileStorage


# task提供任务信息，每个task尤其仅有一个执行者，archive存task可能需要上交的文件
# 由于task已经保存了执行者，则archive仅需返回类型、文档url等

task_fields = {
    'title': fields.String,
    'desc': fields.String,
    'assignee': fields.Integer,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'deadline': fields.DateTime(dt_format='iso8601'),
    'finish': fields.Boolean
}


class TaskListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def post(self, tid):
        """团队队长向特定成员发布工作任务"""
        self.reqparser.add_argument('title', type=str, required=True, location='json')
        self.reqparser.add_argument('desc', type=str, location='json')
        self.reqparser.add_argument('assignee', type=int, required=True, location='json')
        self.reqparser.add_argument('deadline', type=inputs.datetime_from_iso8601, required=True, location='json')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if team.leader != user.id:
            raise ForbiddenError('仅本团队队长可发布工作任务')

        t = Task(**args)
        team.tasks.append(t)

        db.session.add_all([t, team])
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(t, task_fields)}
        return response, 201

    def get(self, tid):
        """团队成员查看团队任务"""
        self.reqparser.add_argument('status', type=inputs.int_range(0, 2), default=2, location='args')
        # 未完成、完成、全部 对应 0、1、2
        self.reqparser.add_argument('self', type=inputs.boolean, default=False, location='args')
        # 是否仅返回自己的任务
        self.reqparser.add_argument('page', type=int, default=1, location='args')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if not team.users.filter_by(id=user.id).count():
            raise ForbiddenError('不可查看其他团队的任务')

        query = team.tasks
        if args.status in (0, 1,):
            query = query.filter_by(finish=args.status)
        if args.self:
            query = query.filter_by(assignee=user.id)

        pagination = query.order_by(Task.datetime.desc()).paginate(
            page=args.page,
            per_page=TASK_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'archives': marshal(pagination.items, task_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


class TaskAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def store_file(self, file):
        return ''

    def post(self, tid):
        """该任务负责人在此提交文件、设置完成状态"""
        self.reqparser.add_argument('text', type=str, dest='content', location=['json', 'form'])
        self.reqparser.add_argument('file', type=FileStorage, dest='content', location='files')
        self.reqparser.add_argument('type', type=inputs.int_range(1, 3), location=['json', 'form'])
        # 当不带type参数则表示，没有需要提交的文件
        self.reqparser.add_argument('desc', type=str, location=['json', 'form'])
        self.reqparser.add_argument('finish', type=inputs.boolean, required=True, location=['json', 'form'])
        args = self.reqparser.parse_args(strict=True)

        task = Task.query.get_or_404(tid)
        user = g.current_user

        if task.assignee != user.id:
            raise ForbiddenError('仅该任务指定的执行者可提交')

        task.finish = args.pop('finish')

        if args.type in (1, 2,):  # 属于.md或.rtf字符串
            a = Archive(**args)
            task.archives.append(a)
        elif args.type == 3:
            args.content = self.store_file(args.content)
            # todo 存储文件，返回存储的path

        task.archives.append(a)
        db.session.add_all([a, task])
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(a, task_detail_fields)}
        return response, 200


# data = {'pages': pagination.pages, 'total': pagination.total,
#         'archives': marshal(pagination.items, archive_fields)}
api.add_resource(TaskListAPI, '/teams/<int:tid>/tasks')
api.add_resource(TaskAPI, '/tasks/<int:tid>')
