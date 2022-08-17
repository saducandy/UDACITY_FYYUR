import os
SECRET_KEY = os.urandom(32)
# Grabs the folder where the script runs.
basedir = os.path.abspath(os.path.dirname(__file__))

# Enable debug mode.
DEBUG = True
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Connect to the database
# toy password for assignment (Windows required it), not real world best practice!
SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:3195@localhost:5432/fyyurr_04'
