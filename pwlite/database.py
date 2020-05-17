# -*- coding: utf-8 -*-
from flask import current_app
from peewee import Proxy
from playhouse.sqlite_ext import SqliteExtDatabase
import os


class DatabaseProxy(Proxy):

    def pick(self, db_name):
        if db_name != ':memory:':
            db_name = os.path.join(current_app.config['DB_PATH'], db_name)
        db = SqliteExtDatabase(
            db_name,
            # Recommended settings from peewee docs:
            # http://docs.peewee-orm.com/en/latest/peewee/database.html#recommended-settings
            pragmas={
                'cache_size': -1024 * 64,  # 64MB page-cache.
                'journal_mode': 'wal',  # Use WAL-mode (you should always use this!).
                'foreign_keys': 1,
                'ignore_check_constraints': 0,
                "synchronous": 0  # Let the OS manage syncing.
            }
        )
        self.initialize(db)
        self.connect()
