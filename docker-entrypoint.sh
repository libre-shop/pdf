#!/bin/sh

if [ "$ENVIRONMENT" = "production" ]; then
  exec gunicorn -w 4 -b 0.0.0.0:1111 src.app:app
else
  exec python3 src/app.py
fi
