#!/bin/bash
set -e

echo "--- Current Python Version ---"
python --version

echo "--- Upgrading pip ---"
python -m pip install --upgrade pip

echo "--- Installing Python Dependencies (using PyMySQL) ---"
python -m pip install -r requirements.txt

# Optional: Migrations (if DB is accessible during build)
# echo "--- Running Database Migrations ---"
# python manage.py migrate --noinput

echo "--- Collecting Static Files ---"
python manage.py collectstatic --noinput --clear

echo "--- Build Script Finished ---"