#!/bin/bash

echo "Setting up CampusNexus..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please update .env with your configuration"
fi

# Create media and static directories
mkdir -p media/event_banners
mkdir -p media/event_qr_codes
mkdir -p media/payment_screenshots
mkdir -p media/profiles
mkdir -p staticfiles

# Run migrations
python manage.py makemigrations
python manage.py migrate

echo "Setup complete!"
echo "Next steps:"
echo "1. Update .env with your configuration"
echo "2. Create a superuser: python manage.py createsuperuser"
echo "3. Run the server: python manage.py runserver"

