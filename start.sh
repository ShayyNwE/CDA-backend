#!/bin/bash

# ✅ Appliquer toutes les migrations
python manage.py migrate --noinput

python manage.py seed

# ✅ Lancer Gunicorn
gunicorn backend.wsgi