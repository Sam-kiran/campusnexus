"""Management command to create sample data for testing."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import User
from events.models import Event, Registration
from feedback.models import Feedback
import random


class Command(BaseCommand):
    help = 'Create sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create sample admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@saividya.ac.in',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('Created admin user'))
        
        # Create sample organizer
        organizer, created = User.objects.get_or_create(
            username='organizer',
            defaults={
                'email': 'organizer@saividya.ac.in',
                'role': 'organizer',
            }
        )
        if created:
            organizer.set_password('organizer123')
            organizer.save()
            self.stdout.write(self.style.SUCCESS('Created organizer user'))
        
        # Create sample students
        departments = ['Computer Science', 'Electronics', 'Mechanical', 'Civil', 'Electrical']
        categories = ['tech', 'sports', 'cultural', 'academic', 'workshop']
        
        for i in range(1, 11):
            student, created = User.objects.get_or_create(
                username=f'student{i}',
                defaults={
                    'email': f'student{i}@saividya.ac.in',
                    'role': 'student',
                    'department': random.choice(departments),
                    'student_id': f'STU{i:04d}',
                }
            )
            if created:
                student.set_password('student123')
                student.save()
                self.stdout.write(self.style.SUCCESS(f'Created student {i}'))
        
        # Create sample events
        students = User.objects.filter(role='student')
        event_titles = [
            'Tech Hackathon 2024',
            'Sports Day',
            'Cultural Fest',
            'Python Workshop',
            'Robotics Competition',
            'Music Concert',
            'Debate Competition',
            'Coding Challenge',
            'Art Exhibition',
            'Science Fair',
        ]
        
        for i, title in enumerate(event_titles):
            event_date = timezone.now() + timedelta(days=random.randint(1, 30))
            event, created = Event.objects.get_or_create(
                title=title,
                defaults={
                    'description': f'Description for {title}. Join us for an exciting event!',
                    'department': random.choice(departments),
                    'category': random.choice(categories),
                    'rules': f'Rules for {title}. Follow all guidelines.',
                    'event_date': event_date,
                    'location': f'Location {i+1}',
                    'capacity': random.randint(20, 100),
                    'fee': random.choice([0, 50, 100, 200, 500]),
                    'is_team_event': random.choice([True, False]),
                    'team_size': random.randint(2, 5) if random.choice([True, False]) else 1,
                    'created_by': organizer,
                    'status': 'approved',
                    'qr_code_data': f'UPI: event{i}@pay',
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created event: {title}'))
                
                # Create some registrations
                num_registrations = random.randint(5, min(event.capacity, 20))
                for j in range(num_registrations):
                    student = random.choice(students)
                    reg, created = Registration.objects.get_or_create(
                        event=event,
                        user=student,
                        defaults={
                            'payment_status': 'verified',
                            'is_verified': True,
                            'payment_verification_code': f'TXN{random.randint(1000, 9999)}',
                        }
                    )
                    if created:
                        event.total_registrations += 1
                
                event.save()
                event.update_hotness_score()
                
                # Create some feedback for past events
                if event.event_date < timezone.now():
                    for reg in Registration.objects.filter(event=event, is_verified=True)[:5]:
                        Feedback.objects.get_or_create(
                            event=event,
                            user=reg.user,
                            defaults={
                                'rating': random.randint(3, 5),
                                'comment': f'Great event! Really enjoyed it.',
                                'emotion': random.choice(['😊', '😍', '😎', '🙂']),
                                'sentiment_label': 'positive',
                                'is_anonymous': random.choice([True, False]),
                            }
                        )
        
        self.stdout.write(self.style.SUCCESS('Sample data created successfully!'))
        self.stdout.write('Login credentials:')
        self.stdout.write('Admin: admin / admin123')
        self.stdout.write('Organizer: organizer / organizer123')
        self.stdout.write('Students: student1-10 / student123')

