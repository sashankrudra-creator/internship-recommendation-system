from django import forms
from .models import UserProfile, Internship

class StudentForm(forms.Form):
    skills = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your skills (e.g. Python, SQL)'}),
        label="Skills"
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['skills', 'resume', 'profile_photo']
        widgets = {
            'skills': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control', 
                'placeholder': 'List your skills separated by commas...'
            }),
            'resume': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'profile_photo': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }

class LoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class InternshipForm(forms.ModelForm):
    class Meta:
        model = Internship
        fields = ['title', 'company_name', 'location', 'skills_required', 'interest_area', 'education_level', 'stipend', 'duration', 'application_url']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Internship Title (e.g. Web Developer)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Location (e.g. Bangalore, Remote)'}),
            'skills_required': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Skills required (comma separated)'}),
            'interest_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Interest Area (e.g. Data Science)'}),
            'education_level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Education Level (e.g. B.Tech)'}),
            'stipend': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Stipend (e.g. 7000)'}),
            'duration': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Duration in months (e.g. 3)'}),
            'application_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'Application URL (e.g. https://company.com/apply)'}),
        }
