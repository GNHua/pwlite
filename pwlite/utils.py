# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash, abort, current_app, request
from peewee import DoesNotExist, SelectQuery
from datetime import timezone
import os
import math
import glob


def flash_errors(form, category='warning'):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash('{0} - {1}'.format(getattr(form, field).label.text, error), category)


def xstr(s):
    return s or ''


def get_object_or_404(query_or_model, *query):
    if not isinstance(query_or_model, SelectQuery):
        query_or_model = query_or_model.select()
    try:
        return query_or_model.where(*query).get()
    except DoesNotExist:
        abort(404)


def calc_page_num(current_page_number, total_page_number):
    if total_page_number <= 7:
        start_page_number, end_page_number = 1, total_page_number
    elif current_page_number - 3 < 1:
        start_page_number, end_page_number = 1, 7
    elif current_page_number + 3 > total_page_number:
        start_page_number, end_page_number = total_page_number - 6, total_page_number
    else:
        start_page_number, end_page_number = current_page_number - 3, current_page_number + 3

    return start_page_number, end_page_number


def get_pagination_kwargs(d, current_page_number, total_page_number):
    d['current_page_number'] = current_page_number
    d['total_page_number'] = total_page_number
    d['start_page_number'], d['end_page_number'] = \
        calc_page_num(d['current_page_number'], d['total_page_number'])


def paginate(query):
    current_page_number = request.args.get('page', default=1, type=int)
    number_per_page = 100
    total_page_number = math.ceil(query.count() / number_per_page)
    query = query.paginate(current_page_number, paginate_by=number_per_page)
    kwargs = dict(data=query.execute(), number_per_page=number_per_page)
    get_pagination_kwargs(kwargs, current_page_number, total_page_number)
    return kwargs


def convert_utc_to_local(datetime):
    return datetime.replace(tzinfo=timezone.utc).astimezone(current_app.config['TIMEZONE'])


def get_active_wiki_groups():
    suffix_len = len(current_app.config['ACTIVE_DB_SUFFIX'])
    return [
        os.path.basename(fn)[:-suffix_len] \
        for fn in glob.glob(os.path.join(
            current_app.config['DB_PATH'], 
            f'*{current_app.config["ACTIVE_DB_SUFFIX"]}'
        ))
    ]


def get_inactive_wiki_groups():
    suffix_len = len(current_app.config['INACTIVE_DB_SUFFIX'])
    return [
        os.path.basename(fn)[:-suffix_len] \
        for fn in glob.glob(os.path.join(
            current_app.config['DB_PATH'], 
            f'*{current_app.config["INACTIVE_DB_SUFFIX"]}'
        ))
    ]


def wiki_group_active(wiki_group):
    return wiki_group in get_active_wiki_groups()


def wiki_group_inactive(wiki_group):
    return wiki_group in get_inactive_wiki_groups()
