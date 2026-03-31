#!/bin/bash

# ✅ Appliquer toutes les migrations
python manage.py migrate --noinput

# ✅ Lancer Gunicorn
gunicorn backend.wsgi