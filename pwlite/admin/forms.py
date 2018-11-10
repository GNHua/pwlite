# -*- coding: utf-8 -*-
"""Admin forms."""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp


class AddWikiGroupForm(FlaskForm):
    wiki_group_name = StringField(
        'Wiki Group Name',
        validators=[
            DataRequired('Please enter a wiki group name.'),
            Regexp(
                '^[\w+ ]+$', 
                message='Wiki group name must contain only letters, '
                        'numbers, underscore, and whitespace.'
            )
        ]
    )
    add = SubmitField('Add')
