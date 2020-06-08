from . import db
from config import Config, DEFAULT_AVATAR

from sqlalchemy import Column, String, Integer
from sqlalchemy import ForeignKey, Date, DateTime, Time
from sqlalchemy.dialects.mysql import TINYINT, BOOLEAN

from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired, BadSignature

from passlib.apps import mysql_context as pwd_context
from secrets import token_urlsafe


class User(db.Model):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(64), nullable=False)  # 但email最长可以到320位?
    username = Column(String(16), unique=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    name = Column(String(16), index=True)  # 昵称
    avatar = Column(String(40), default=DEFAULT_AVATAR)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(Config.SECRET_KEY, expires_in=expiration)
        return s.dumps({'uid': self.id})
        # return s.dumps({'uid': self.id, 'time': time()})  todo 发布时恢复

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(Config.SECRET_KEY)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        return User.query.get(data['uid'])

    def alter(self, kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)
        return self


t_users = db.Table('t_users',
                   Column('team_id', Integer, db.ForeignKey('teams.id')),
                   Column('user_id', Integer, db.ForeignKey('users.id'))
                   )
# 关联表r； u -> v: 多->多; u,v -> r: 一->多

foreign_conf = {'lazy': 'dynamic', 'passive_deletes': True, 'cascade': "all, delete-orphan"}
# lazy使得查询时返回查询对象；passive_deletes/cascade用于级联删除
# passive一般与受关联表中 ondelete='CASCADE'搭配，这两样一般可省 , cascade="all, delete-orphan"


class Team(db.Model):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True)
    leader = Column(Integer)
    name = Column(String(16), unique=False)
    desc = Column(String(64))
    check_s = Column(Time, index=True)
    check_e = Column(Time, index=True)
    inv_code = Column(String(16), unique=True)  # 邀请码
    users = db.relationship('User', secondary=t_users, backref='teams', lazy='dynamic')
    schedules = db.relationship('Schedule', backref='team', **foreign_conf)
    attendances = db.relationship('Attendance', backref='team', **foreign_conf)

    @property
    def tid(self):
        return self.id

    def alter(self, kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)
        return self

    def renew_inv_code(self):  # 16位base64，冲突可能性仅 1/2^256
        new_code = token_urlsafe(12)
        while self.__class__.query.filter_by(inv_code=new_code).first():
            new_code = token_urlsafe(12)
        self.inv_code = new_code


class Schedule(db.Model):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True)
    desc = Column(String(32), nullable=False)
    urgency = Column(TINYINT)  # 对应三种紧急程度, 似乎只支持str；不灵活
    start = Column(Date, nullable=False, index=True)
    end = Column(Date, nullable=False, index=True)
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'))

    def alter(self, kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)
        return self


class Attendance(db.Model):
    __tablename__ = "attendances"
    id = Column(Integer, primary_key=True)
    uid = Column(Integer, nullable=False)
    datetime = Column(DateTime, index=True, nullable=False)
    punctual = Column(BOOLEAN, nullable=False)  # 以免将来团队更换打卡时间无从判断
    team_id = Column(Integer, ForeignKey('teams.id', ondelete='CASCADE'))

    def alter(self, kwargs):
        for k, v in kwargs.items():
            if v is not None:
                setattr(self, k, v)
        return self
