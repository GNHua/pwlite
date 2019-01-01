# -*- coding: utf-8 -*-
from flask import g, current_app, request
from datetime import datetime

from pwlite.extensions import db
from pwlite.wiki.forms import SearchForm
from pwlite.models import WikiPage, WikiKeypage
from pwlite.utils import convert_utc_to_local


def decorate_blueprint(blueprint):

    @blueprint.url_defaults
    def add_wiki_group_code(endpoint, values):
        if 'wiki_group' in values:
            return
        try:
            values.setdefault('wiki_group', g.wiki_group)
        except AttributeError:
            pass

    @blueprint.url_value_preprocessor
    def pull_wiki_group_code(endpoint, values):
        g.wiki_group = values.pop('wiki_group')
        if g.wiki_group not in current_app.active_wiki_groups:
            abort(404)

    @blueprint.before_request
    def open_database_connection():
        db.pick('{0}.db'.format(g.wiki_group))

    @blueprint.after_request
    def close_database_connection(response):
        db.close()
        return response

    # Docs: http://flask.pocoo.org/docs/1.0/templating/#context-processors
    @blueprint.context_processor
    def inject_wiki_group_data():
        if g.wiki_group not in current_app.active_wiki_groups:
            return dict()

        if request.endpoint in [
            'wiki.edit', 'wiki.upload',
            'auth.login', 'auth.logout'
        ]:
            return dict(wiki_group=g.wiki_group)

        search_form = SearchForm()

        query = (WikiPage
                 .select(WikiPage.id, WikiPage.title)
                 .join(
                     WikiKeypage,
                     on=(WikiKeypage.wiki_page))
                 .order_by(WikiKeypage.id))
        wiki_keypages = query.execute()

        # TODO: enhancement - this might be a performance bottleneck in the future.
        query = (WikiPage
                 .select(WikiPage.id, WikiPage.title, WikiPage.modified_on)
                 .order_by(WikiPage.modified_on.desc())
                 .limit(5))
        wiki_changes = query.execute()

        latest_change_time = convert_utc_to_local(wiki_changes[0].modified_on)
        now = convert_utc_to_local(datetime.utcnow())

        if latest_change_time.date() == now.date():
            latest_change_time = latest_change_time.strftime('[%H:%M]')
        else:
            latest_change_time = latest_change_time.strftime('[%b %d]')

        return dict(
            wiki_group=g.wiki_group,
            search_form=search_form,
            wiki_keypages=wiki_keypages,
            wiki_changes=wiki_changes,
            latest_change_time=latest_change_time,
            convert_utc_to_local=convert_utc_to_local
        )