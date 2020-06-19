from flask_socketio import Namespace, join_room, leave_room, emit, rooms
from .. import socketio, db
from ..models import Team, User

r_members = socketio.server.manager.rooms


class ChatRoom(Namespace):
    def __init__(self, namespace):
        super().__init__(namespace)

    # def on_connect(self):
        # print('连接上了', request.sid)

    # def on_disconnect(self):
        # print('关闭了连接', request.sid)

    def on_join(self, data):
        tid = data.pop('tid', 0)
        team = Team.query.get_or_404(tid)
        user = User.verify_auth_token(data.pop('token', ''))

        if not user or not db.session.query(team.users.filter_by(id=user.id).exists()).scalar():
            return

        join_room(tid)
        # print('有人加入了！')

        # emit('onlineCount', {'online': g.tid}, room=request.sid)
        emit('enter', {'uid': user.id}, broadcast=True, room=tid)

    def on_leave(self, data):
        tid = data.pop('tid', 0)
        if tid not in rooms():
            return
        leave_room(tid)
        # print('有人离开了！')
        emit('exit', {'uid': data.get('uid')}, broadcast=True, room=tid)

    def on_chat(self, data):
        """原样转发客户端发送的json"""

        tid = data.get('tid', 0)
        if tid not in rooms():
            return
        # print('有人在聊天！')
        emit('chat', data, broadcast=True, room=tid)  # , include_self=False


socketio.on_namespace(ChatRoom('/chat'))
