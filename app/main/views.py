from . import main


@main.route('/img/<string:avatar>')
def get_avatar(avatar):
    pass


@main.route('/archives/<string:filename>')
def get_archive(filename):
    pass
