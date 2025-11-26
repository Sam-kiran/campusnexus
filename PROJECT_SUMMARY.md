# CampusNexus - Project Summary

## Overview
CampusNexus is a comprehensive full-stack application for managing campus-wide events, tracking registrations, gathering anonymous feedback, and analyzing participation. The system streamlines student engagement, event organization, and feedback analytics through unified dashboards for both students and administrators.

## Architecture

### Backend
- **Framework**: Django 4.2.7
- **Database**: PostgreSQL
- **Authentication**: Supabase integration
- **Task Queue**: Celery + Redis for async tasks
- **API**: Django REST Framework

### Frontend
- **Framework**: Django Templates with Bootstrap 5
- **Calendar**: FullCalendar.js
- **Charts**: Chart.js
- **Color Scheme**: Modern gradient-based design using the provided palette

### AI/ML Features
- **Chatbot**: OpenAI GPT-3.5 for student queries
- **Sentiment Analysis**: Hugging Face BERT model (cardiffnlp/twitter-roberta-base-sentiment-latest)
- **AI Assistant**: Event creation with AI

## Key Features Implemented

### 1. User Management
- ✅ Custom User model with role-based access (Student, Admin, Organizer)
- ✅ Supabase authentication integration
- ✅ College email domain validation
- ✅ Separate signup/login for students and admin/organizer
- ✅ Students cannot signup as admin/organizer

### 2. Event Management
- ✅ Full CRUD operations for events
- ✅ Event fields: title, department, category, rules, date/time, location, capacity, fee
- ✅ QR code generation for payment
- ✅ Banner upload
- ✅ Event approval workflow (Admin only)
- ✅ Hot events algorithm (weighted: 60% registrations, 40% ratings)
- ✅ Event recommendations based on department and interests
- ✅ FullCalendar.js integration ready

### 3. Registration System
- ✅ Student registration with QR code payment
- ✅ Payment verification module
- ✅ Duplicate registration prevention
- ✅ Team event support
- ✅ Payment screenshot upload
- ✅ Verification workflow for admin/organizer

### 4. Feedback & Ratings
- ✅ 1-5 star ratings
- ✅ Optional comments (max 500 characters, 100 words limit)
- ✅ Emotion selection (8 emotions)
- ✅ Anonymous feedback option
- ✅ Sentiment analysis using BERT
- ✅ Average ratings displayed on event pages
- ✅ Duplicate feedback prevention
- ✅ Compulsory feedback after event completion

### 5. Dashboard & Analytics

#### Admin/Organizer Dashboard
- ✅ Event statistics
- ✅ Participation analytics
- ✅ Department-wise stats (Chart.js)
- ✅ Category-wise stats
- ✅ Sentiment analysis trends
- ✅ Time-based trends
- ✅ Export reports (PDF/CSV)
- ✅ Top performing events

#### Student Dashboard
- ✅ Browse and register for events
- ✅ View registered events (upcoming and past)
- ✅ View events needing feedback
- ✅ Leaderboard integration
- ✅ Hot events display
- ✅ Event recommendations

### 6. AI Features
- ✅ Chatbot for student queries
  - Event search ("Show me tech events tomorrow")
  - Registration status
  - Feedback reminders
  - General queries via OpenAI
- ✅ AI Assistant for event creation (Admin/Organizer)
  - Generate event descriptions
  - Suggest categories and departments
  - Create complete event structure
- ✅ Sentiment Analysis
  - Real-time sentiment scoring
  - Positive/Neutral/Negative classification
  - Sentiment trends visualization

### 7. Notifications & Reminders
- ✅ Celery + Redis integration
- ✅ Pre-event reminders (24 hours before)
- ✅ Post-event feedback reminders
- ✅ Scheduled tasks (daily at 9 AM, 10 AM, midnight)
- ✅ Email notifications

### 8. Leaderboard
- ✅ Points system (10 per event + 5 per feedback)
- ✅ Rank calculation
- ✅ Top 100 display
- ✅ Auto-update via Celery task

### 9. Deployment Ready
- ✅ Docker configuration
- ✅ Docker Compose setup
- ✅ Production-ready settings
- ✅ Environment variable management
- ✅ Static file handling
- ✅ Media file handling

## Project Structure

```
CampusNexus/
├── campusnexus/          # Main project
│   ├── settings.py      # Configuration
│   ├── urls.py          # URL routing
│   ├── wsgi.py          # WSGI config
│   ├── asgi.py          # ASGI config
│   └── celery.py        # Celery config
├── users/               # User management
│   ├── models.py       # User, Leaderboard
│   ├── views.py        # Auth views
│   ├── utils.py        # Supabase integration
│   └── management/     # Management commands
├── events/              # Event management
│   ├── models.py       # Event, Registration, Recommendation
│   ├── views.py        # CRUD views
│   ├── tasks.py        # Celery tasks
│   └── utils.py        # Recommendations, poster generation
├── feedback/           # Feedback system
│   ├── models.py       # Feedback, Analytics
│   ├── views.py        # Feedback views
│   └── utils.py        # Sentiment analysis
├── dashboard/          # Dashboards
│   ├── views.py        # Student/Admin dashboards
│   └── utils.py        # Export functions
├── chatbot/            # AI features
│   ├── views.py        # Chatbot, AI assistant
│   └── utils.py        # Query processing, AI generation
├── templates/          # HTML templates
│   ├── base.html       # Base template with color scheme
│   ├── users/          # Auth templates
│   ├── events/         # Event templates
│   ├── feedback/       # Feedback templates
│   ├── dashboard/     # Dashboard templates
│   └── chatbot/        # Chatbot templates
├── static/             # Static files
├── media/              # User uploads
├── requirements.txt   # Dependencies
├── Dockerfile         # Docker config
├── docker-compose.yml # Docker Compose
└── README.md          # Documentation
```

## Color Scheme Implementation

The application uses the provided color palette throughout:
- **Hēi Sè Black (#142030)**: Primary background, navbar
- **Siesta Tan (#E9D8C8)**: Text color, form inputs
- **Stellar Strawberry (#FF5C8D)**: Primary buttons, accents, hot badges
- **Pico Eggplant (#732553)**: Card headers, gradients
- **Blue Whale (#1E3442)**: Cards, secondary elements
- **Grauzone (#85A3B2)**: Borders, secondary text

Gradients are used extensively for buttons, headers, and visual elements.

## API Endpoints

### Events
- `GET /events/` - List events
- `GET /events/<id>/` - Event detail
- `POST /events/create/` - Create event
- `GET /events/api/hot-events/` - Hot events API
- `GET /events/api/recommendations/` - Recommendations API

### Feedback
- `POST /feedback/event/<id>/create/` - Create feedback
- `GET /feedback/api/event/<id>/stats/` - Statistics API

### Dashboard
- `GET /dashboard/student/` - Student dashboard
- `GET /dashboard/admin/` - Admin dashboard
- `GET /dashboard/leaderboard/` - Leaderboard
- `GET /dashboard/api/analytics/` - Analytics API

### Chatbot
- `POST /chatbot/api/query/` - Chatbot query
- `POST /chatbot/api/create-event/` - AI event creation
- `POST /chatbot/api/generate-poster/` - Poster generation

## Environment Variables Required

```env
SECRET_KEY
DEBUG
DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
OPENAI_API_KEY
COLLEGE_EMAIL_DOMAIN
CELERY_BROKER_URL, CELERY_RESULT_BACKEND
EMAIL_* (for email notifications)
```

## Setup Instructions

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure environment**: Copy `.env.example` to `.env` and update
3. **Run migrations**: `python manage.py migrate`
4. **Create superuser**: `python manage.py createsuperuser`
5. **Run server**: `python manage.py runserver`

Or use Docker:
```bash
docker-compose up --build
```

## Testing

Run tests with:
```bash
python manage.py test
```

## Deployment

The application is ready for deployment on:
- **Render**: Configure environment variables
- **AWS**: Use Elastic Beanstalk or EC2
- **Heroku**: Use Postgres and Redis addons

## Future Enhancements

Potential improvements:
- FullCalendar.js calendar view implementation
- DALL-E integration for poster generation
- Advanced recommendation algorithms
- Real-time notifications (WebSockets)
- Mobile app (React Native)
- Advanced analytics with Pandas
- Integration with payment gateways

## License

MIT License

