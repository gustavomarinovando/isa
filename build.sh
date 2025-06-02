#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Installing System Dependencies (for mysqlclient) ---"
# The Vercel build environment is based on Amazon Linux 2, which uses yum.
# We need mariadb-devel (provides MySQL C headers), gcc (for compilation),
# and python3-devel (for Python C extensions).
sudo yum update -y
sudo yum install -y mariadb-devel gcc python3-devel

echo "--- Installing Python Dependencies ---"
# Now that system dependencies are in place, install Python packages.
pip install -r requirements.txt

echo "--- Collecting Static Files ---"
# Run Django's collectstatic command.
python manage.py collectstatic --noinput

echo "--- Build Script Finished ---"