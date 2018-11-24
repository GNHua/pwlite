# -*- coding: utf-8 -*-
"""Admin section"""
from flask import Blueprint, flash, redirect, render_template, request, \
    url_for, send_from_directory, current_app
import os
import shutil
from peewee import IntegrityError

from pwlite.utils import flash_errors, get_object_or_404
from pwlite.extensions import db
from pwlite.settings import ADMIN_DB, DB_PATH
from pwlite.models import WikiGroup, WikiPage, WikiPageIndex, \
    WikiPageVersion, WikiReference, WikiFile, WikiKeypage
from pwlite.admin.forms import AddWikiGroupForm

blueprint = Blueprint('admin', __name__, static_folder='../static')

@blueprint.before_request
def open_database_connection():
    db.pick(ADMIN_DB)


@blueprint.after_request
def close_database_connection(response):
    db.close()
    return response


@blueprint.route('/')
def home():
    """Cover page."""
    query = (WikiGroup
             .select()
             .where(WikiGroup.active==True))
    active_wiki_groups = query.execute()
    return render_template(
        'admin/cover.html',
        active_wiki_groups=active_wiki_groups
    )


@blueprint.route('/super_admin', methods=['GET', 'POST'])
def super_admin():
    """Manage wiki groups."""
    all_wiki_groups = WikiGroup.select().execute()
    form = AddWikiGroupForm()

    # Create a new wiki group with its own database and static file directory
    if form.validate_on_submit():
        new_wiki_group_name = form.wiki_group_name.data
        new_db_name = new_wiki_group_name.replace(' ', '')

        # Save the name of the new wiki group in database `_admin`
        # Remove whitespaces in the wiki group name.
        # Then use it to name the database which is about to be initialized.
        try:
            new_wiki_group = WikiGroup.create(
                name=new_wiki_group_name,
                db_name=new_db_name,
                active=True
            )
            os.mkdir(os.path.join(DB_PATH, new_wiki_group.db_name))
            query = WikiGroup.select().where(WikiGroup.active==True)
            current_app.active_wiki_groups = [
                wiki_group.db_name for wiki_group in query.execute()
            ]

            db.close()
            db.pick(new_wiki_group.db_filename())
            db.create_tables([
                WikiPage,
                WikiPageIndex,
                WikiPageVersion,
                WikiReference,
                WikiFile,
                WikiKeypage
            ])

            # Create wiki group home page, and the id is 1.
            WikiPage.create(title='Home')
            flash('New wiki group added', 'info')
            return redirect(url_for('.super_admin'))

        except IntegrityError:
            flash('Wiki Group already exists', 'warning')
        except FileExistsError:
            flash('Upload directory already exists.', 'warning')

    else:
        flash_errors(form)

    return render_template(
        'admin/super_admin.html',
        form=form,
        all_wiki_groups=all_wiki_groups
    )


@blueprint.route('/activate/<wiki_group>')
def activate(wiki_group):
    try:
        wg = (WikiGroup
              .select()
              .where(WikiGroup.db_name==wiki_group)
              .get())
        wg.active = not wg.active
        wg.save()
        query = WikiGroup.select().where(WikiGroup.active==True)
        current_app.active_wiki_groups = [
            wiki_group.db_name for wiki_group in query.execute()
        ]
    except WikiGroup.DoesNotExist:
        pas
    return redirect(url_for('.super_admin'))


@blueprint.route('/delete-group/<wiki_group>')
def delete_group(wiki_group):
    # remove wiki group record in _admin.db
    WikiGroup.delete().where(WikiGroup.db_name==wiki_group).execute()
    # remove the database file
    os.remove(os.path.join(DB_PATH, '{0}.db'.format(wiki_group)))
    # remove uploaded files
    shutil.rmtree(os.path.join(DB_PATH, wiki_group))
    return redirect(url_for('.super_admin'))


# TODO: maybe move these routes to another blueprint
@blueprint.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(blueprint.static_folder, 'images'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
