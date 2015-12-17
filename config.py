import os
basedir = os.path.abspath(os.path.dirname(__file__))

CSRF_ENABLED = True
SECRET_KEY = 'you-will-never-guess'

if os.environ.get('DATABASE_URL') is None:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
else:
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']

OAUTH_CREDENTIALS = {
    'facebook': {
        'id': '1902095766682336',
        'secret': 'cb846832e14382f2b48788d8f3f98f4e'
    },
    'twitter': {
        'id': '4QeliSQmG2eDodyYWQ4wk44UL',
        'secret': '48YAwFbJHFjiXwlEP2mJMTohf6DiDL6cwSxI5BIWzrsqBKtvf4'
    }
}

PLIVO_AUTH = {
    'id': 'MAMTE3OGQ5ZTK4MTI3ZT',
    'token': 'NTRhOTljZjFjYjkwZTVlYzA3YjBmMDg2NWI3YjE2'
}
