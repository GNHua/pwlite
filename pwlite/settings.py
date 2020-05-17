# -*- coding: utf-8 -*-
"""Application configuration.

Most configuration is set via environment variables.

For local development, use a .env file to set
environment variables.
"""
from environs import Env
import os
from datetime import timezone, timedelta

env = Env()
env.read_env()

ENV = env.str('FLASK_ENV', default='production')
DEBUG = ENV == 'development'
SECRET_KEY = env.str('SECRET_KEY')
DEBUG_TB_ENABLED = DEBUG
DEBUG_TB_INTERCEPT_REDIRECTS = False
WTF_CSRF_TIME_LIMIT = 100000000
DATA_PATH = env.str('DATA_PATH', default=os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'data')))
DB_PATH = os.path.join(DATA_PATH, 'db')
ACTIVE_DB_SUFFIX = '.sqlite3'
INACTIVE_DB_SUFFIX = '.sqlite3-inactive'
TIMEZONE = timezone(timedelta(hours=-7), 'MDT') # Mountain Daylight Time