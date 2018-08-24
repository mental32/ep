import flask

blueprint = flask.Blueprint(__name__, 'index')

@blueprint.route('/')
@blueprint.route('/index')
def index():
	return flask.render_template('index.html', bot=flask.current_app.bot)

@blueprint.route('/profile/<int:guild_id>')
def test_profile(guild_id):
	return f'{flask.escape(repr(flask.current_app.bot.get_guild(guild_id)))}'
