@echo off
echo Setting up CampusNexus...

REM Create directories
if not exist "media\event_banners" mkdir "media\event_banners"
if not exist "media\event_qr_codes" mkdir "media\event_qr_codes"
if not exist "media\payment_screenshots" mkdir "media\payment_screenshots"
if not exist "media\profiles" mkdir "media\profiles"
if not exist "staticfiles" mkdir "staticfiles"

REM Create .env if it doesn't exist
if not exist ".env" (
    copy ".env.example" ".env"
    echo .env file created from .env.example
    echo Please update .env with your configuration
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Update .env with your configuration
echo 2. Install dependencies: pip install -r requirements.txt
echo 3. Run migrations: python manage.py migrate
echo 4. Create superuser: python manage.py createsuperuser
echo 5. Run server: python manage.py runserver
echo.
pause

