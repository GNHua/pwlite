# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_wtf.csrf import CSRFProtect

from pwlite.database import DatabaseProxy

csrf_protect = CSRFProtect()
db = DatabaseProxy()

from pwlite.markdown import WikiMarkdown

markdown = WikiMarkdown()