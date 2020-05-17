# -*- coding: utf-8 -*-
"""Create an application instance."""
from pwlite.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(port=31415, debug=True)