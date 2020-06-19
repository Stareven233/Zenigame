from app import create_app, socketio
from flask_cors import CORS

app = create_app()
#  修改了flask_uploads里关于Werkzeug secure_filename等的导入
CORS(app, supports_credentials=True)


if __name__ == '__main__':
    # create_db_table(app)
    socketio.run(app, host='0.0.0.0', debug=False)
    # app.run(debug=True)
