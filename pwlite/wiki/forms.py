# -*- coding: utf-8 -*-
"""Wiki forms."""
from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField, IntegerField, StringField
from wtforms.validators import DataRequired


class WikiEditForm(FlaskForm):
    textArea = TextAreaField('Edit')
    submit = SubmitField('Save Changes')
    current_version = IntegerField('Current version')


class RenameForm(FlaskForm):
    new_title = StringField(
        'New page title',
        validators=[
            DataRequired()
        ]
    )
    submit = SubmitField('Rename')


class SearchForm(FlaskForm):
    keyword = StringField('Search')
    start_date = StringField()
    end_date = StringField()
    submit = SubmitField('Search')


class KeyPageEditForm(FlaskForm):
    textArea = TextAreaField('Edit')
    submit = SubmitField('Save Changes')


class HistoryRecoverForm(FlaskForm):
    version = IntegerField(
        'Recover history',
        validators=[DataRequired('Please enter a version number.')]
    )
    submit = SubmitField('Submit')
