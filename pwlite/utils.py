# -*- coding: utf-8 -*-
"""Helper utilities and decorators."""
from flask import flash, abort
from peewee import DoesNotExist, SelectQuery
from datetime import timezone

from pwlite.settings import TIMEZONE


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


def format_datetime(datetime):
    dt = datetime.replace(tzinfo=timezone.utc).astimezone(TIMEZONE)
    return dt.strftime('%Y-%m-%d %H:%M:%S ') + dt.tzname()
