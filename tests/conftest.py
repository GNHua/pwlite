# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from webtest import TestApp
import os

from pwlite.app import create_app
from pwlite.extensions import db as _db
from pwlite.models import WikiGroup
from pwlite.models import *
from .factories import WikiGroupFactory

MODELS = [
    WikiGroup,
    WikiPage,
    WikiPageIndex,
    WikiPageVersion,
    WikiReference,
    WikiFile
]


@pytest.fixture
def app():
    """An application for the tests."""
    _app = create_app('tests.settings')
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def testapp(app):
    """A Webtest app."""
    return TestApp(app)


@pytest.fixture
def db():
    """A test database for the tests."""
    _db.pick(':memory:')
    _db.create_tables(MODELS)

    yield _db

    _db.drop_tables(MODELS)
    _db.close()


@pytest.fixture
def wiki_group(db):
    """A wiki group for the tests."""
    _wiki_group = WikiGroupFactory.create()
    return _wiki_group
