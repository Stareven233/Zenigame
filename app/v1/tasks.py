from flask import g, url_for
from flask_restful import Resource, reqparse, inputs, marshal, fields

from . import api
from ..models import Team, Task, Archive, Log
from .. import db
from .decorators import auth
from .exceptions import ForbiddenError, NotFound

from config import TASK_PER_PAGE, FILE_PER_PAGE, Config
from werkzeug.datastructures import FileStorage
from uuid import uuid4
from datetime import datetime
from os import remove, path


# task提供任务信息，每个task尤其仅有一个执行者，archive存task可能需要上交的文件
# 由于task已经保存了执行者，则archive仅需返回类型、文档url等

task_fields = {
    'id': fields.Integer,
    'title': fields.String,
    'desc': fields.String,
    'assignee': fields.Integer,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'deadline': fields.DateTime(dt_format='iso8601'),
    'finish': fields.Boolean
}


class ArchiveUrl(fields.Url):
    def output(self, key, obj):
        value = getattr(obj, key if self.attribute is None else self.attribute)
        endpoint = ('v1.archive', 'main.get_archive')[obj.type == 3]
        return url_for(endpoint, _external=self.absolute, filename=value)


class ArchiveItem(fields.Raw):
    def format(self, value):
        return marshal(value, archive_fields)


archive_fields = {
    'name': fields.String,
    'type': fields.Integer,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'archive_url': ArchiveUrl(attribute='filename', absolute=True)
}
task_detail_fields = task_fields.copy()
task_detail_fields['archives'] = fields.List(ArchiveItem, attribute='archives')
# todo 如果前端没用到detail_fields中重复的信息，就去掉，仅返回archives


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

        # if not team.users.filter_by(id=args.assignee).count():
        if not db.session.query(team.users.filter_by(id=args.assignee).exists()).scalar():
            raise ForbiddenError('所选的负责人不是团队成员')

        t = Task(**args)
        team.tasks.append(t)

        log = Log(uid=user.id, desc=f'创建了任务: {args.title}')
        team.logs.append(log)

        db.session.add_all((t, log,))
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(t, task_fields)}
        return response, 201

    def get(self, tid):
        """团队成员查看团队任务"""

        self.reqparser.add_argument('status', type=inputs.int_range(0, 2), default=2, location='args')
        # 未完成、完成、全部 对应 0、1、2
        self.reqparser.add_argument('uid', type=int, default=0, location='args')
        # 仅返回该用户的任务，放空(此时为0)则返回全部的
        self.reqparser.add_argument('page', type=int, default=1, location='args')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        # if not team.users.filter_by(id=user.id).count():
        if not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的任务')

        query = team.tasks
        if args.status in (0, 1,):
            query = query.filter_by(finish=args.status)
        if args.uid:
            # 由于只能给本团队成员发任务，当uid不是该团队成员自然没有记录
            query = query.filter_by(assignee=args.uid)

        pagination = query.order_by(Task.datetime.desc()).paginate(
            page=args.page,
            per_page=TASK_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'tasks': marshal(pagination.items, task_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


def store_archive(file):
    filename = file.filename.rstrip('"')
    # 很奇怪，当文件名带中文时后缀有多余的"，如 'xxx.doc"'
    name = uuid4().hex + '.' + filename.rsplit('.', 1)[1]
    file.save(Config.UPLOADED_FILES_DEST + f'archives/{name}')
    return name


def remove_archive(archives):
    for a in archives:
        p = Config.UPLOADED_FILES_DEST + f'archives/{a.filename}'
        if path.isfile(p):
            remove(p)


class TaskAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def post(self, tid):
        """该任务负责人在此提交文件、设置完成状态"""

        self.reqparser.add_argument('text', type=str, dest='content', location=['json', 'form'])
        self.reqparser.add_argument('file', type=FileStorage, location='files')
        self.reqparser.add_argument('type', type=inputs.int_range(1, 3), location=['json', 'form'])
        # 当不带type参数，则表示没有需要提交的文件
        self.reqparser.add_argument('name', type=str, location=['json', 'form'])
        # 文件名，不带后缀（区别于archive.filename，后者是生成的uuid，用于url，且有后缀）
        self.reqparser.add_argument('finish', type=inputs.boolean, required=True, location=['json', 'form'])
        args = self.reqparser.parse_args(strict=True)

        task = Task.query.get_or_404(tid)
        user = g.current_user

        if task.assignee != user.id:
            raise ForbiddenError('仅该任务指定的执行者可提交')

        if task.finish:
            raise ForbiddenError('该任务已完成，不可再提交')

        task.finish = args.pop('finish')
        file = args.pop('file')

        if args.type is None:
            # 仅更新task.finish时
            db.session.add(task)
        else:
            # 需要提交文档/文件时
            if args.type in (1, 2,) and args.get('content'):
                args.filename = uuid4().hex + '.' + ('', 'md', 'rtf')[args.type]

            elif args.type == 3 and file:
                # 非文本字符串(md/rtf)存于硬盘，文件名写入数据库
                args.filename = store_archive(file)
            else:
                raise ForbiddenError('文件缺失')

            a = Archive(**args)
            task.team.archives.append(a)
            task.archives.append(a)
            db.session.add(a)  # 像这里有外键约束，不必add task

        if task.finish:
            log = Log(uid=user.id, desc=f'完成了任务: {task.title}')
            task.team.logs.append(log)
            db.session.add(log)

        if task.finish:
            log = Log(uid=user.id, desc=f'完成了任务: {task.title}')
            task.team.logs.append(log)
            db.session.add(log)

        db.session.commit()
        response = {'code': 0, 'message': '', 'data': marshal(task, task_detail_fields)}
        return response, 201

    def get(self, tid):
        task = Task.query.get_or_404(tid)

        if not db.session.query(task.team.users.filter_by(id=g.current_user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的任务')

        response = {'code': 0, 'message': '', 'data': marshal(task, task_detail_fields)}
        return response, 200

    def patch(self, tid):
        self.reqparser.add_argument('title', type=str, location='json')
        self.reqparser.add_argument('desc', type=str, location='json')
        self.reqparser.add_argument('assignee', type=int, location='json')
        self.reqparser.add_argument('deadline', type=inputs.datetime_from_iso8601, location='json')
        args = self.reqparser.parse_args(strict=True)

        task = Task.query.get_or_404(tid)
        user = g.current_user

        if task.team.leader != user.id:
            raise ForbiddenError('仅本团队队长可修改工作任务')

        task.alter(args)
        task.datetime = datetime.now()

        log = Log(uid=user.id, desc=f'修改了任务: {task.title}')
        task.team.logs.append(log)

        db.session.add_all((task, log))
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200

    def delete(self, tid):
        """注意，删除任务后它关联的文档也会被删除"""

        task = Task.query.get_or_404(tid)

        if task.team.leader != g.current_user.id:
            raise ForbiddenError('仅本团队队长可删除工作任务')

        archives = task.archives.filter_by(type=3).all()
        remove_archive(archives)

        log = Log(uid=g.current_user.id, desc=f'删除了任务: {task.title}')
        task.team.logs.append(log)

        db.session.delete(task)
        db.session.add(log)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200


class ArchiveListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()
        self.reqparser.add_argument('page', type=int, default=1, location='args')

    def get(self, tid):
        """获取某个团队的所有文件，分页"""

        args = self.reqparser.parse_args(strict=True)
        team = Team.query.get_or_404(tid)

        if not db.session.query(team.users.filter_by(id=g.current_user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的文件')

        pagination = team.archives.order_by(Archive.datetime.desc()).paginate(
            page=args.page,
            per_page=FILE_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'archives': marshal(pagination.items, archive_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


class ArchiveAPI(Resource):
    """
    仅实现获取与删除，若修改则先删除再重建
    type=3，即文件类无法在此由get得到，它由nginx代理。但简单起见，文件却是由此处的delete删除...
    """

    decorators = [auth.login_required]

    def get(self, filename):
        """
        关于Archive的属性都能在 'get task' 中获取，故与nginx一样，这里仅返回文本本身
        若是type=3的文件类则返回空字符串
        """

        a = Archive.query.filter(Archive.filename == filename).first()  # todo 改成exists
        if a is None:
            raise NotFound('该文档不存在')

        return a.content, 200

    def delete(self, filename):
        """按文件名删除某个文档/文件"""

        a = Archive.query.filter(Archive.filename == filename).first()
        if a is None:
            raise NotFound('该文档不存在')

        task = a.task
        user = g.current_user

        if user.id not in (task.team.leader, task.assignee):
            raise ForbiddenError('仅队长或其发布者可删除')

        task.archives.remove(a)
        if a.type == 3:
            remove_archive([a])

        db.session.delete(a)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200


api.add_resource(TaskListAPI, '/teams/<int:tid>/tasks', endpoint='tasks')
api.add_resource(TaskAPI, '/tasks/<int:tid>', endpoint='task')
api.add_resource(ArchiveListAPI, '/teams/<int:tid>/archives', endpoint='archives')
api.add_resource(ArchiveAPI, '/archives/<string:filename>', endpoint='archive')
