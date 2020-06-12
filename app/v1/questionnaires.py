from flask import g
from flask_restful import Resource, reqparse, inputs, marshal, fields

from . import api
from ..models import Team, Questionnaire, QQuestion, QOption
from .. import db
from .decorators import auth
from .exceptions import ForbiddenError

from config import QUESTIONNAIRE_PER_PAGE


class OptionItem(fields.Raw):
    def format(self, value):
        return marshal(value, option_fields)


class QuestionItem(fields.Raw):
    def format(self, value):
        return marshal(value, question_fields)


class IsFilled(fields.Raw):
    def output(self, key, obj):
        records = getattr(obj, self.attribute)
        cnt = records.filter_by(username=g.current_user.username).count()
        return bool(cnt)


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
    'questions': fields.List(QuestionItem),  # todo 设成仅questionnaire_detail_fields中获取
    # 'filled': IsFilled(attribute='records'),  # 仅表示发出get的该用户是否填写了此问卷
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
        # todo 或许利用class的__slot__可以验证携带的参数
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if team.leader != user.id:
            raise ForbiddenError('仅本团队队长可发布调查问卷')

        questions = args.pop('questions')
        questionnaire = Questionnaire(**args)

        for q in questions:
            ops = q.pop('options')
            qq = QQuestion(**q)  # 先假设参数都是正确的

            for op in ops:
                # 简答题ops==[]，不会执行该语句块
                qo = QOption(**op)  # 也假设参数都正确
                qq.options.append(qo)

            questionnaire.questions.append(qq)
            # 会自动根据外键分析，故题目与选项不需 session.add

        team.questionnaires.append(questionnaire)
        db.session.add(questionnaire)
        db.session.commit()

        response = {'code': 0, 'message': '', 'data': marshal(questionnaire, questionnaire_fields)}
        return response, 201

    def get(self, tid):
        """团队成员查看团队问卷"""
        self.reqparser.add_argument('page', type=int, default=1, location='args')
        args = self.reqparser.parse_args(strict=True)

        team = Team.query.get_or_404(tid)
        user = g.current_user

        if not team.users.filter_by(id=user.id).count():
            raise ForbiddenError('不可查看其他团队的问卷')

        pagination = team.questionnaires.query.order_by(Questionnaire.datetime.desc()).paginate(
            page=args.page,
            per_page=QUESTIONNAIRE_PER_PAGE
        )

        data = {'pages': pagination.pages, 'total': pagination.total,
                'questionnaire': marshal(pagination.items, questionnaire_fields)}

        response = {'code': 0, 'message': '', 'data': data}
        return response, 200


api.add_resource(QuestionnaireListAPI, '/teams/<int:tid>/questionnaires')
# todo 单条问卷的获取、填写、删除 API
# todo 导出问卷结果的 API
