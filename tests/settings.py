"""Settings module for test app."""
import os


ENV = 'development'
TESTING = True
SECRET_KEY = 'not-so-secret-in-tests'
DEBUG_TB_ENABLED = False
CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
WTF_CSRF_ENABLED = False  # Allows form testing
DB_PATH = os.path.abspath(os.path.dirname(__file__))
