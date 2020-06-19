from flask import g
from flask_restful import Resource, reqparse, inputs, marshal, fields
from sqlalchemy.exc import IntegrityError

from . import api
from ..models import Team, Questionnaire, QQuestion, QOption, Log
from ..models import QRecord, QAnswer
from .. import db
from .decorators import auth
from .exceptions import ForbiddenError, BadRequestError

from config import QUESTIONNAIRE_PER_PAGE
import re
from datetime import datetime
from json import loads as json_loads


class OptionItem(fields.Raw):
    def format(self, value):
        return marshal(value, option_fields)


class IsFilled(fields.Raw):
    def output(self, key, obj):
        q = getattr(obj, self.attribute).filter_by(username=g.current_user.username)
        return db.session.query(q.exists()).scalar()


class AnswerItem(fields.Raw):
    def format(self, value):
        # value.ans = (json_loads, str,)[value.type == 3](value.ans)
        # 恢复单选多选答案的格式
        # 不可行：sqlalchemy.exc.InvalidRequestError: This Session's transaction has been rolled back...
        return marshal(value, answer_fields)


class AnsItem(fields.Raw):
    def output(self, key, obj):
        ans = getattr(obj, key)

        if getattr(obj, 'type') in (1, 2,):
            ans = json_loads(ans)
        return ans


option_fields = {
    'oid': fields.Integer,
    'desc': fields.String,
}
question_fields = {
    'qid': fields.Integer,
    'desc': fields.String,
    'type': fields.Integer,
    'options': fields.List(OptionItem),
}
questionnaire_fields = {
    'id': fields.Integer,
    'title': fields.String,
    'desc': fields.String,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'deadline': fields.DateTime(dt_format='iso8601'),
    'filled': IsFilled(attribute='records'),
    # 仅表示发出get的该用户自身是否填写了此问卷
}

answer_fields = {
    'qid': fields.Integer,
    'type': fields.Integer,
    'ans': AnsItem,
    # 已在AnswerItem里处理过格式
}
record_fields = {
    'username': fields.String,
    'datetime': fields.DateTime(dt_format='iso8601'),
    'answers': fields.List(AnswerItem),
}


class QuestionnaireListAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def post(self, tid):
        """团队队长发布团队调查问卷"""

        self.reqparser.add_argument('title', type=str, required=True, location='json')
        self.reqparser.add_argument('desc', type=str, location='json')
        self.reqparser.add_argument('deadline', type=inputs.datetime_from_iso8601, required=True, location='json')
        self.reqparser.add_argument('questions', type=list, required=True, location='json')
        # questions 应是题目列表，每个题目又含选项列表
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if team.leader != user.id:
            raise ForbiddenError('仅本团队队长可发布调查问卷')

        questions = args.pop('questions')
        questionnaire = Questionnaire(**args)
        team.questionnaires.append(questionnaire)

        try:
            # 手动验证多层嵌套的json参数，实际上实名问卷也不怕乱填，都有记录
            for q in questions:
                ops = q.pop('options') or []
                qq = QQuestion(**q)

                for op in ops:
                    # 简答题ops==[]，不会执行该语句块
                    qo = QOption(**op)
                    qq.options.append(qo)

                questionnaire.questions.append(qq)
                # 会自动根据外键分析，故题目与选项不需 session.add
        except TypeError as e:
            # ee = "多余参数: " + str(e).split(' is ', 1)[0][1:-1]
            ee = "多余参数: " + re.findall(r"'(.*?)' is", str(e))[0]
            raise BadRequestError(ee)

        try:
            db.session.add(questionnaire)
            db.session.commit()
        except IntegrityError as e:
            ee = "缺失参数: " + re.findall(r"Column \\\'(\w+)\\\'", repr(e))[0]
            raise BadRequestError(ee)

        log = Log(uid=g.current_user.id, desc=f'创建了问卷: {questionnaire.title}')
        team.logs.append(log)
        db.session.add(log)
        db.session.commit()  # 上方为了验证参数要跟这里分开

        response = {'code': 0, 'message': '', 'data': marshal(questionnaire, questionnaire_fields)}
        return response, 201

    def get(self, tid):
        """团队成员查看团队问卷列表"""

        self.reqparser.add_argument('page', type=int, default=1, location='args')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的问卷')

        pagination = team.questionnaires.order_by(Questionnaire.datetime.desc()).paginate(
            page=args.page,
            per_page=QUESTIONNAIRE_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'questionnaire': marshal(pagination.items, questionnaire_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


class QuestionnaireAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def get(self, qid):
        """
        团队成员查看单个问卷，仅返回题目部分，与 QuestionnaireListAPI.get 互补
        考虑到问卷一发布就不可修改，应该没必要像 Task.get 一样再次连简要信息一起返回
        """

        questionnaire = Questionnaire.query.get_or_404(qid)
        user = g.current_user

        if not db.session.query(questionnaire.team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可查看其他团队的问卷')

        response = {'code': 0, 'message': '', 'data': [marshal(q, question_fields) for q in questionnaire.questions]}
        return response, 200

    def post(self, qid):
        """团队成员填写问卷"""

        self.reqparser.add_argument('answers', type=list, required=True, location='json')
        # answers 应是答案列表，里面每个对象包含题号qid、类型type、内容ans
        args = self.reqparser.parse_args(strict=True)

        questionnaire = Questionnaire.query.get_or_404(qid)
        user = g.current_user

        if not db.session.query(questionnaire.team.users.filter_by(id=user.id).exists()).scalar():
            raise ForbiddenError('不可填写其他团队的问卷')

        if datetime.now() > questionnaire.deadline:
            raise ForbiddenError('已超过问卷截止时间')

        # if db.session.query(exists().where(QRecord.questionnaire_id==qid, QRecord.username==user.username)).scalar():
        if db.session.query(questionnaire.records.filter_by(username=user.username).exists()).scalar():
            raise ForbiddenError('你已填写了该问卷')

        record = QRecord(username=user.username)
        questionnaire.records.append(record)

        try:
            for answer in args.answers:
                if 'ans' in answer:
                    answer['ans'] = str(answer['ans'])  # 选择题题号以str形式存
                a = QAnswer(**answer)
                record.answers.append(a)

        except TypeError as e:
            ee = "多余参数: " + re.findall(r"'(.*?)' is", str(e))[0]
            raise BadRequestError(ee)

        try:
            db.session.add(record)
            db.session.commit()
        except IntegrityError as e:
            ee = "缺失参数: " + re.findall(r"Column \\\'(\w+)\\\'", repr(e))[0]
            raise BadRequestError(ee)

        response = {'code': 0, 'message': ''}
        return response, 201

    def delete(self, qid):
        """团队队长删除单个问卷"""

        questionnaire = Questionnaire.query.get_or_404(qid)
        user = g.current_user

        if not questionnaire.team.leader == user.id:
            raise ForbiddenError('仅团队队长可删除问卷')

        team = questionnaire.team
        team.questionnaires.remove(questionnaire)

        log = Log(uid=user.id, desc=f'删除了问卷: {questionnaire.title}')
        team.logs.append(log)

        db.session.delete(questionnaire)
        db.session.add(log)
        db.session.commit()

        response = {'code': 0, 'message': ''}
        return response, 200


class QuestionnaireRecAPI(Resource):
    decorators = [auth.login_required]

    def __init__(self):
        self.reqparser = reqparse.RequestParser()

    def get(self, qid):
        """团队队长获取该问卷调查结果，非匿名"""

        questionnaire = Questionnaire.query.get_or_404(qid)
        user = g.current_user

        if not questionnaire.team.leader == user.id:
            raise ForbiddenError('仅团队队长可查看结果')

        # response = {'code': 0, 'message': '', 'data': marshal(questionnaire.records.all(), record_fields)}
        response = {'code': 0, 'message': '', 'data': [marshal(r, record_fields) for r in questionnaire.records]}
        return response, 200


api.add_resource(QuestionnaireListAPI, '/teams/<int:tid>/questionnaires')
api.add_resource(QuestionnaireAPI, '/questionnaires/<int:qid>')
api.add_resource(QuestionnaireRecAPI, '/questionnaires/<int:qid>/records')
