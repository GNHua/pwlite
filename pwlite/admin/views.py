# -*- coding: utf-8 -*-
"""Admin section"""
from flask import Blueprint, flash, redirect, render_template, request, \
    url_for, send_from_directory, current_app
import os
import glob
import shutil
from peewee import IntegrityError

from pwlite.utils import flash_errors, get_object_or_404, get_active_wiki_groups, \
    get_inactive_wiki_groups, wiki_group_active, wiki_group_inactive
from pwlite.extensions import db
from pwlite.models import WikiPage, WikiPageIndex, WikiPageVersion, \
    WikiReference, WikiFile, WikiKeypage
from pwlite.admin.forms import AddWikiGroupForm

blueprint = Blueprint('admin', __name__, static_folder='../static')


@blueprint.route('/')
def home():
    """Cover page."""
    return render_template(
        'admin/cover.html',
        active_wiki_groups=get_active_wiki_groups()
    )


@blueprint.route('/super_admin', methods=['GET', 'POST'])
def super_admin():
    """Manage wiki groups."""
    active_wiki_groups = get_active_wiki_groups()
    inactive_wiki_groups = get_inactive_wiki_groups()
    all_wiki_groups = active_wiki_groups + inactive_wiki_groups
    form = AddWikiGroupForm()

    # Create a new wiki group with its own database and static file directory
    if form.validate_on_submit():
        new_wiki_group_name = form.wiki_group_name.data
        if new_wiki_group_name in all_wiki_groups:
            flash('Wiki Group already exists. Please remove it and try again.', 'warning')
        if os.path.exists(os.path.join(current_app.config['DB_PATH'], new_wiki_group_name)):
            flash('Upload directory already exists. Please remove it and try again.', 'warning')

        # make the folder for uploaded files
        os.mkdir(os.path.join(current_app.config['DB_PATH'], new_wiki_group_name))

        db.pick(f'{new_wiki_group_name}{current_app.config["ACTIVE_DB_SUFFIX"]}')
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
        db.close()

        flash('New wiki group added', 'info')
        return redirect(url_for('.super_admin'))

    else:
        flash_errors(form)

    # merge all wiki groups into one list and mark active/inactive
    all_wiki_groups_sorted = []
    for wiki_group in active_wiki_groups:
        all_wiki_groups_sorted.append((wiki_group, True))
    for wiki_group in inactive_wiki_groups:
        all_wiki_groups_sorted.append((wiki_group, False))
    all_wiki_groups_sorted.sort()

    return render_template(
        'admin/super_admin.html',
        form=form,
        all_wiki_groups_sorted=all_wiki_groups_sorted
    )


@blueprint.route('/activate/<wiki_group>')
def activate(wiki_group):
    db_path = current_app.config['DB_PATH']
    active_db_fn = f'{wiki_group}{current_app.config["ACTIVE_DB_SUFFIX"]}'
    active_db_fn = os.path.join(db_path, active_db_fn)
    inactive_db_fn = f'{wiki_group}{current_app.config["INACTIVE_DB_SUFFIX"]}'
    inactive_db_fn = os.path.join(db_path, inactive_db_fn)

    if wiki_group_active(wiki_group):
        os.rename(active_db_fn, inactive_db_fn)
    elif wiki_group_inactive(wiki_group):
        os.rename(inactive_db_fn, active_db_fn)

    return redirect(url_for('.super_admin'))


@blueprint.route('/delete-group/<wiki_group>')
def delete_group(wiki_group):
    db_path = current_app.config['DB_PATH']
    active_db_fn = f'{wiki_group}{current_app.config["ACTIVE_DB_SUFFIX"]}'
    active_db_fn = os.path.join(db_path, active_db_fn)
    inactive_db_fn = f'{wiki_group}{current_app.config["INACTIVE_DB_SUFFIX"]}'
    inactive_db_fn = os.path.join(db_path, inactive_db_fn)
    upload_folder = os.path.join(db_path, wiki_group)

    if wiki_group_active(wiki_group):
        # remove the database file
        os.remove(active_db_fn)
        # remove uploaded files
        shutil.rmtree(upload_folder)
    elif wiki_group_inactive(wiki_group):
        os.remove(inactive_db_fn)
        shutil.rmtree(upload_folder)

    return redirect(url_for('.super_admin'))


# TODO: maybe move these routes to another blueprint
@blueprint.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(blueprint.static_folder, 'images'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )
