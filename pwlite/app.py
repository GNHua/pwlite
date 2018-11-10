# -*- coding: utf-8 -*-
"""The app module, containing the app factory function."""
from flask import Flask, render_template
import os

from pwlite import commands, admin, wiki
from pwlite.extensions import csrf_protect, db
from pwlite.models import WikiGroup


def create_app(config_object='pwlite.settings'):
    """An application factory, as explained here: http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split('.')[0])
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    register_errorhandlers(app)
    register_shellcontext(app)
    register_commands(app)
    register_database(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    csrf_protect.init_app(app)
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(admin.views.blueprint)
    app.register_blueprint(wiki.views.blueprint)
    return None


def register_errorhandlers(app):
    """Register error handlers."""
    def render_error(error):
        """Render error template."""
        # If a HTTPException, pull the `code` attribute; default to 500
        error_code = getattr(error, 'code', 500)
        return render_template('{0}.html'.format(error_code)), error_code
    for errcode in [401, 404, 500]:
        app.errorhandler(errcode)(render_error)
    return None


def register_shellcontext(app):
    """Register shell context objects."""
    def shell_context():
        """Shell context objects."""
        return {
            'db': db,
            'WikiPage': wiki.models.WikiPage}

    app.shell_context_processor(shell_context)


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.test)
    app.cli.add_command(commands.lint)
    app.cli.add_command(commands.clean)
    app.cli.add_command(commands.urls)


def register_database(app):
    admin_db_exists = not os.path.exists(app.config['ADMIN_DB'])
    db.pick(app.config['ADMIN_DB'])
    if not admin_db_exists:
        db.create_tables([WikiGroup])
    query = WikiGroup.select().where(WikiGroup.active==True)
    app.active_wiki_groups = [
        wiki_group.db_name for wiki_group in query.execute()
    ]
    db.close()
