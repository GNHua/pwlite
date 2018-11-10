# -*- coding: utf-8 -*-
"""Factories to help in tests."""
from factory import Sequence
from factory_peewee import PeeweeModelFactory

from pwlite.extensions import db
from pwlite.models import *


class BaseFactory(PeeweeModelFactory):
    """Base factory."""

    class Meta:
        """Factory configuration."""

        database = db


class WikiGroupFactory(BaseFactory):
    """Wiki group factory."""

    name = Sequence(lambda n: 'wiki group {0}'.format(n))
    db_name = Sequence(lambda n: 'wikigroup{0}'.format(n))
    active = True

    class Meta:
        """Factory configuration."""

        model = WikiGroup


# class WikiPage(BaseFactory):
#     title = CharField(unique=True)
#     markdown = TextField(null=True)
#     html = TextField(null=True)
#     current_version = IntegerField(default=1)
#     modified_on = DateTimeField(default=datetime.utcnow)

