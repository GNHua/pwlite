# -*- coding: utf-8 -*-
import os
import logging
import time
from waitress import serve

from pwlite.settings import DATA_PATH
from autoapp import app

# Because Gunicorn does not run on Windows, a pure Python WSGI 
# server, called Waitress, is used for Windows.
# Waitress sends its logging output (including application exception 
# renderings) to the Python logger object named waitress. 
# Details: https://docs.pylonsproject.org/projects/waitress/en/latest/#logging
logger = logging.getLogger('waitress')
logger_filename = os.path.join(DATA_PATH, 'logs', '{0}.log'.format(time.strftime('%Y%m%d')))
format = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(
    filename=logger_filename,
    filemode='a',
    format=format,
    level=logging.INFO
)
app.logger.addHandler(logger)
serve(app, listen='127.0.0.1:31415', threads=1)