from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    skills = models.TextField(blank=True, default="")
    resume = models.FileField(upload_to='resumes/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    last_activity = models.DateTimeField(default=timezone.now)

    def is_online(self):
        # Consider user online if active in the last 5 minutes
        now = timezone.now()
        return self.last_activity > now - datetime.timedelta(minutes=5)

    def __str__(self):
        return self.user.username

class Internship(models.Model):
    title = models.CharField(max_length=255, default="Internship Role")
    company_name = models.CharField(max_length=255, default="Unknown Company", blank=True, null=True)
    location = models.CharField(max_length=255)
    skills_required = models.TextField()
    interest_area = models.CharField(max_length=255, blank=True, null=True)
    education_level = models.CharField(max_length=255, blank=True, null=True)
    stipend = models.CharField(max_length=100, blank=True, null=True)
    duration = models.CharField(max_length=100, blank=True, null=True)
    application_url = models.URLField(max_length=500, blank=True, null=True)
    WORK_TYPES = [
        ('In-office', 'In-office'),
        ('Work from Home', 'Work from Home'),
        ('Field work', 'Field work'),
        ('Hybrid', 'Hybrid'),
    ]
    work_type = models.CharField(max_length=50, choices=WORK_TYPES, default='In-office')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name} - {self.location}"

    @property
    def numeric_stipend(self):
        if not self.stipend: return 0
        import re
        nums = re.findall(r'\d+', str(self.stipend))
        return int(nums[0]) if nums else 0
    def skills_list(self):
        if not self.skills_required:
            return []
        import re
        # Handle cases where skills might be wrapped in quotes from CSV
        items = re.split(r'[;,]', str(self.skills_required))
        return [item.strip().strip('"').strip() for item in items if item.strip()]

class Application(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='applications')
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name='applicants')
    applied_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="Applied") # Applied, Reviewing, Accepted, Rejected

    class Meta:
        unique_together = ('user', 'internship')

    def __str__(self):
        return f"{self.user.username} applied to {self.internship.company_name}"

class SavedInternship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_internships')
    internship = models.ForeignKey(Internship, on_delete=models.CASCADE, related_name='saves')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'internship')

    def __str__(self):
        return f"{self.user.username} saved {self.internship.company_name}"
