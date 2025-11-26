# CampusNexus - Centralized Campus Event & Feedback System

A comprehensive full-stack application for managing campus-wide events, tracking registrations, gathering anonymous feedback, and analyzing participation.

## Features

### User Roles
- **Student**: View, register, and give feedback on events
- **Admin/Organizer**: Create and manage events, approve events, view analytics, and manage users

### Event Management
- Full CRUD operations for events
- Event fields: title, department, category, rules, date/time, location, capacity, fee, QR code for payment, banner upload
- Event approval workflow
- Hot events algorithm based on registrations and ratings
- Event recommendations based on department and interests

### Registration System
- Student registration with QR code payment
- Payment verification module
- Duplicate registration prevention
- Team event support

### Feedback & Ratings
- 1-5 star ratings with optional comments (max 500 characters, 100 words)
- Emotion selection
- Anonymous feedback option
- Sentiment analysis using BERT model
- Average ratings displayed on event pages

### Dashboard & Analytics
- **Admin/Organizer Dashboard**: 
  - Event statistics
  - Participation analytics
  - Department-wise and category-wise stats
  - Sentiment analysis trends
  - Export reports (PDF/CSV)
  
- **Student Dashboard**:
  - Browse and register for events
  - View registered events
  - View past events
  - Leaderboard
  - Compulsory event feedback after completion

### AI Features
- **Chatbot**: Answer student queries about events
- **AI Assistant**: Create events using AI (Admin/Organizer only)
- **Sentiment Analysis**: Analyze feedback using Hugging Face BERT model

### Notifications
- Pre-event reminders via email
- Post-event feedback reminders
- Automated scheduling with Celery + Redis

## Tech Stack

- **Backend**: Django 4.2.7
- **Database**: PostgreSQL
- **Authentication**: Supabase
- **Task Queue**: Celery + Redis
- **AI/ML**: OpenAI API, Hugging Face Transformers
- **Frontend**: Bootstrap 5, FullCalendar.js, Chart.js
- **Containerization**: Docker
- **Deployment**: Ready for Render/AWS/Heroku

## Color Scheme

The application uses a modern color palette:
- **Hēi Sè Black**: #142030
- **Siesta Tan**: #E9D8C8
- **Stellar Strawberry**: #FF5C8D
- **Pico Eggplant**: #732553
- **Blue Whale**: #1E3442
- **Grauzone**: #85A3B2

## Setup Instructions

### Prerequisites
- Python 3.11+
- PostgreSQL
- Redis
- Docker (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd CampusNexus
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DB_NAME=campusnexus
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_SERVICE_KEY=your-supabase-service-key
OPENAI_API_KEY=your-openai-api-key
COLLEGE_EMAIL_DOMAIN=@saividya.ac.in
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

5. **Run migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Run development server**
```bash
python manage.py runserver
```

### Docker Setup

1. **Build and run with Docker Compose**
```bash
docker-compose up --build
```

2. **Run migrations in container**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

## Project Structure

```
CampusNexus/
├── campusnexus/          # Main project settings
├── users/                # User management app
├── events/               # Event management app
├── feedback/             # Feedback and ratings app
├── dashboard/            # Dashboard and analytics app
├── chatbot/              # AI chatbot and assistant app
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS, images)
├── media/                # User uploaded files
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
├── docker-compose.yml   # Docker Compose configuration
└── README.md            # This file
```

## API Endpoints

### Events
- `GET /events/` - List all events
- `GET /events/<id>/` - Event detail
- `POST /events/create/` - Create event (Admin/Organizer)
- `GET /events/api/hot-events/` - Hot events API
- `GET /events/api/recommendations/` - Event recommendations API

### Feedback
- `POST /feedback/event/<id>/create/` - Create feedback
- `GET /feedback/api/event/<id>/stats/` - Feedback statistics API

### Dashboard
- `GET /dashboard/student/` - Student dashboard
- `GET /dashboard/admin/` - Admin dashboard
- `GET /dashboard/leaderboard/` - Leaderboard
- `GET /dashboard/api/analytics/` - Analytics API

### Chatbot
- `POST /chatbot/api/query/` - Chatbot query
- `POST /chatbot/api/create-event/` - Create event with AI
- `POST /chatbot/api/generate-poster/` - Generate event poster

## Testing

Run tests with:
```bash
python manage.py test
```

## Deployment

The application is ready for deployment on:
- **Render**: Configure environment variables and deploy
- **AWS**: Use Elastic Beanstalk or EC2
- **Heroku**: Use Heroku Postgres and Redis addons

### Production Checklist
- Set `DEBUG=False`
- Configure production PostgreSQL
- Set up SSL/HTTPS
- Configure domain
- Set up CI/CD pipeline (GitHub Actions)
- Configure email backend for production

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

"# CampusNexus" 
