"""Management command to update leaderboard."""
from django.core.management.base import BaseCommand
from users.models import Leaderboard, User
from events.models import Registration
from feedback.models import Feedback
from django.db.models import Q


class Command(BaseCommand):
    help = 'Update leaderboard scores and ranks'

    def handle(self, *args, **options):
        self.stdout.write('Updating leaderboard...')
        
        for user in User.objects.filter(role='student'):
            leaderboard, created = Leaderboard.objects.get_or_create(user=user)
            
            # Count verified registrations
            leaderboard.total_events_attended = Registration.objects.filter(
                user=user,
                is_verified=True
            ).count()
            
            # Count feedback given
            leaderboard.total_feedback_given = Feedback.objects.filter(user=user).count()
            
            # Calculate points (10 per event + 5 per feedback)
            leaderboard.total_points = (
                leaderboard.total_events_attended * 10 +
                leaderboard.total_feedback_given * 5
            )
            
            leaderboard.save()
        
        # Update ranks
        leaderboards = Leaderboard.objects.order_by('-total_points', '-total_events_attended')
        for rank, leaderboard in enumerate(leaderboards, start=1):
            leaderboard.rank = rank
            leaderboard.save(update_fields=['rank'])
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated leaderboard for {leaderboards.count()} users'))

