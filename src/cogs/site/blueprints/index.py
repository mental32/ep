import flask

blueprint = flask.Blueprint(__name__, 'index')

@blueprint.route('/')
@blueprint.route('/index')
def index():
	return 'Hello world'
