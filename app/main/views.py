from . import main


@main.route('/img/<string:avatar>')
def get_avatar(avatar):
    pass
