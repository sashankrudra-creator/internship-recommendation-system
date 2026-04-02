import pandas as pd
import os
import io
import re
from pypdf import PdfReader
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from .forms import StudentForm, ProfileForm, LoginForm, InternshipForm
from .utils import intern, analyze_skill_gaps
from .models import UserProfile, Internship, Application, SavedInternship

DATA_PATH = "dataset/internships.csv"

def seed_internships_from_csv():
    """Import internships from CSV and remove any that are no longer in the CSV."""
    if not os.path.exists(DATA_PATH):
        return
    
    try:
        df = pd.read_csv(DATA_PATH)
        current_csv_ids = []
        
        import random
        for _, row in df.iterrows():
            # Handle messy column names
            csv_title = str(row.get('Title ', row.get('Title', 'Unknown Internship'))).strip()
            csv_company = str(row.get('Company_Name', '')).strip()
            csv_location = str(row.get('Location', 'Unknown')).strip()
            csv_skills = str(row.get('Skills_Required', '')).strip()
            csv_interest = str(row.get('Interest_Area', '')).strip()
            csv_edu = str(row.get('Education _Level', '')).strip()
            csv_stipend = str(row.get('Stipend (INR)', '')).strip()
            csv_duration = str(row.get('Duration (Months)', '')).strip()
            csv_app_url = str(row.get('Application_URL', '/external-apply-dummy/')).strip()
            
            # Find existing or create new
            internship, created = Internship.objects.get_or_create(
                title=csv_title,
                company_name=csv_company,
                location=csv_location,
                defaults={
                    'skills_required': csv_skills,
                    'interest_area': csv_interest,
                    'education_level': csv_edu,
                    'stipend': csv_stipend,
                    'duration': csv_duration,
                    'application_url': csv_app_url,
                    'work_type': random.choice(['In-office', 'Work from Home', 'Field work', 'Hybrid'])
                }
            )
            
            if not created:
                # Update remaining fields if they changed
                internship.skills_required = csv_skills
                internship.interest_area = csv_interest
                internship.education_level = csv_edu
                internship.stipend = csv_stipend
                internship.duration = csv_duration
                internship.application_url = csv_app_url
                # We won't overwrite work_type if already set to something specific by user,
                # but for seeding, we'll randomize if it's the default "In-office"
                if internship.work_type == 'In-office' and random.random() > 0.5:
                    internship.work_type = random.choice(['Work from Home', 'Field work', 'Hybrid'])
                internship.save()
            
            current_csv_ids.append(internship.id)
            
        # Final Step: Delete everything that is NOT in the ID list we just built
        # This cleans up duplicates (the extra ones not picked by .first())
        # and cleans up stale data no longer in the CSV.
        Internship.objects.exclude(id__in=current_csv_ids).delete()
            
    except Exception as e:
        print(f"Error during strict sync: {e}")

def get_unique_skills():
    """Build a list of all known skills from the database for matching."""
    all_skills = set()
    for s in Internship.objects.values_list('skills_required', flat=True):
        if s:
            for sk in str(s).split(','):
                skill = sk.strip().lower()
                if skill:
                    all_skills.add(skill)
    return sorted(list(all_skills))

# Broad list of common industry skills to improve extraction
COMMON_SKILLS = [
    # Programming Languages
    'Python', 'Java', 'JavaScript', 'C++', 'C#', 'PHP', 'Ruby', 'Swift', 'Kotlin', 'Go', 'Rust', 'C', 'TypeScript', 'Scala', 'Perl', 'Lua', 'R', 'MATLAB', 'Dart',
    
    # Web Development
    'HTML', 'CSS', 'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring', 'ASP.NET', 'Laravel', 'Bootstrap', 'Tailwind', 'Sass', 'Less', 'jQuery', 'Next.js', 'Nuxt.js', 'Svelte', 'FastAPI',
    
    # Databases
    'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Firebase', 'SQLite', 'Oracle', 'Redis', 'Cassandra', 'DynamoDB', 'MariaDB',
    
    # Cloud & DevOps
    'AWS', 'Azure', 'Docker', 'Kubernetes', 'Jenkins', 'Terraform', 'Ansible', 'Google Cloud', 'GCP', 'Heroku', 'Digital Ocean', 'CI/CD', 'Git', 'GitHub', 'GitLab', 'Bitbucket', 'Linux', 'Bash', 'PowerShell', 'Unix',
    
    # Data Science & AI
    'Machine Learning', 'Deep Learning', 'Data Science', 'AI', 'NLP', 'Computer Vision', 'Pandas', 'NumPy', 'Scikit-Learn', 'TensorFlow', 'PyTorch', 'Keras', 'OpenCV', 'Tableau', 'Power BI', 'Matplotlib', 'Seaborn', 'Spark', 'Hadoop', 'Big Data', 'Statistics', 'Mathematics',
    
    # Design
    'UI', 'UX', 'Figma', 'Adobe XD', 'Photoshop', 'Illustrator', 'Canva', 'InDesign', 'After Effects', 'Maya', 'Blender', 'Sketch', 'Zeplin',
    
    # Mobile Development
    'Android', 'iOS', 'Flutter', 'React Native', 'Xamarin', 'Ionic', 'SwiftUI', 'Objective-C',
    
    # Software Engineering & Business
    'Agile', 'Scrum', 'Project Management', 'Software Engineering', 'Unit Testing', 'Integration Testing', 'System Design', 'REST API', 'GraphQL', 'Microservices', 'SDLC',
    'Excel', 'Word', 'PowerPoint', 'Tally', 'Communication', 'Leadership', 'Teamwork', 'Problem Solving', 'Critical Thinking', 'Management', 'Marketing', 'SEO', 'Digital Marketing'
]

def extract_skills_from_pdf(pdf_file):
    try:
        reader = PdfReader(pdf_file)
        full_text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                full_text += content + "\n"
        
        if not full_text.strip():
            return None, "We couldn't extract any text from this PDF."

        # Pre-clean the text a bit to handle weird character spacing some PDFs have
        full_text_cleaned = re.sub(r'\s+', ' ', full_text)

        # 1. Try to find the Skills Section strictly
        skill_headers = ['SKILLS', 'TECHNICAL SKILLS', 'PROFESSIONAL SKILLS', 'EXPERTISE', 'CORE COMPETENCIES', 'TOOLS', 'COMPETENCIES', 'TECHNICAL EXPERTISE', 'SOFTWARE SKILLS', 'IT SKILLS', 'KEY SKILLS', 'SKILLS & ABILITIES', 'AREAS OF STRENGTH']
        header_pattern = r'(?i)(?:\n|^|  )\s*(?:' + '|'.join(map(re.escape, skill_headers)) + r')\s*(?::|\n|-|–|—|$)'
        section_matches = list(re.finditer(header_pattern, full_text))
        
        search_area = full_text # Default to full text
        found_section = False

        if section_matches:
            start_pos = section_matches[0].end()
            # Look for the end of the section by finding the next common header
            next_section_pattern = r'(?i)\n\s*(?:EXPERIENCE|WORK EXPERIENCE|EMPLOYMENT|HISTORY|PROFESSIONAL EXPERIENCE|EDUCATION|ACADEMIC|PROJECTS|KEY PROJECTS|CERTIFICATION|CERTIFICATIONS|AWARDS|HONORS|PUBLICATION|PUBLICATIONS|SUMMARY|PROFESSIONAL SUMMARY|OBJECTIVE|HOBBIES|REFERENCE|REFERENCES|INTERESTS|QUALIFICATIONS|ACHIEVEMENTS|CO-CURRICULAR|DECLARATION)\b'
            next_section = re.search(next_section_pattern, full_text[start_pos:])
            
            if next_section:
                search_area = full_text[start_pos:start_pos + next_section.start()]
            else:
                # If no next section, take a reasonable chunk but not the whole rest if it's huge
                search_area = full_text[start_pos:start_pos + 2000]
            found_section = True

        found_skills = set()
        clean_search_area = search_area.lower()
        
        # 2. Extract known keywords from the search area or full text
        # If we didn't find a section, we search the full text
        text_to_search = clean_search_area if found_section else full_text.lower()
        
        db_skills = get_unique_skills()
        master_list = set(COMMON_SKILLS + db_skills)
        
        skill_map = {s.lower().strip(): s for s in master_list if s.strip()}
        
        for skill_lower, original_skill in skill_map.items():
            # Use bounded matching to avoid partial matches (e.g., 'java' in 'javascript')
            # Handle special characters like C++, C#, etc.
            if len(skill_lower) <= 2 or '+' in skill_lower or '#' in skill_lower or '.' in skill_lower:
                # For short skills or those with special chars, look for common separators
                pattern = r'(?i)(?:\s|^|[,./()\-|:;])' + re.escape(skill_lower) + r'(?:\s|$|[,./()\-|:;])'
            else:
                pattern = r'(?i)\b' + re.escape(skill_lower) + r'\b'
                
            if re.search(pattern, text_to_search):
                found_skills.add(original_skill)

        # 3. If we found a section, also try to grab things that look like skills (comma-separated, bulleted)
        if found_section:
            # Words that are definitely not skills but might appear in a skills section
            blacklist = ['objective', 'education', 'summary', 'university', 'college', 'school', 'resume', 'curriculum', 'vitae', 'name', 'phone', 'email', 'experience', 'career', 'project', 'projects', 'certification', 'certifications', 'award', 'awards', 'hobby', 'hobbies', 'interest', 'interests', 'reference', 'references', 'qualification', 'qualifications', 'achievement', 'achievements', 'intermediate', 'advanced', 'expert', 'proficient', 'knowledge', 'understanding', 'working', 'familiar', 'basic', 'good', 'excellent', 'level', 'skills', 'technical', 'professional', 'competencies']
            
            # Split by various possible delimiters
            tokens = re.split(r'[,\n•●▪|\t*]', search_area)
            for t in tokens:
                # Clean up the token
                t = re.sub(r'[\(\):\-–—]', ' ', t)
                t = t.strip()
                
                # Skill tokens are usually short (1-4 words)
                if 2 < len(t) < 40:
                    words = t.split()
                    if len(words) <= 4:
                        t_lower = t.lower()
                        # Filter out numbers, emails, URLs and blacklisted common words
                        if not any(word in t_lower for word in blacklist) and \
                           not '@' in t_lower and \
                           not any(c.isdigit() for c in t) and \
                           not t_lower.startswith('http'):
                            found_skills.add(t.title())

        if not found_skills:
            return None, "No recognizable skills were detected. Please ensure your resume has a clear 'Skills' section."
            
        # Filter out some more noise (one-word items that are common English words but not skills)
        noise_words = {'The', 'And', 'For', 'With', 'From', 'About', 'Into', 'During', 'Including', 'Between', 'Through'}
        final_skills = [s for s in found_skills if s not in noise_words]
        
        # Return unique, sorted skills
        return ", ".join(sorted(final_skills)), None
    except Exception as e:
        return None, f"Error processing the PDF: {str(e)}"

def signup(request):
    if request.method == "POST":
        uname = request.POST.get('username')
        pword = request.POST.get('password')
        if uname and pword:
            if not User.objects.filter(username=uname).exists():
                user = User.objects.create_user(username=uname, password=pword)
                UserProfile.objects.create(user=user)
                login(request, user)
                return redirect('profile')
    return render(request, "signup.html", {'form': LoginForm()})

@never_cache
@csrf_protect
def user_login(request):
    error = None
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            if user:
                login(request, user)
                if user.is_staff:
                    return redirect('admin_dashboard')
                return redirect('recommendations')
            else:
                error = "Invalid credentials"
    else:
        form = LoginForm()
    return render(request, "login.html", {'form': form, 'error': error})

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            profile_instance = form.save(commit=False)
            if 'resume' in request.FILES:
                extracted, err = extract_skills_from_pdf(request.FILES['resume'])
                if extracted:
                    # Keep original casing from extraction map where possible
                    new_skills_list = [s.strip() for s in extracted.split(',')]
                    
                    if profile_instance.skills:
                        # Existing skills - try to normalize but keep some casing
                        existing = [s.strip() for s in profile_instance.skills.split(',')]
                        
                        # Use a map to merge where keys are lowercase but values are original
                        merged_map = {s.lower(): s for s in existing if s}
                        for s in new_skills_list:
                            if s.lower() not in merged_map:
                                merged_map[s.lower()] = s
                        
                        combined = sorted(merged_map.values(), key=lambda x: x.lower())
                        profile_instance.skills = ", ".join(combined)
                    else:
                        profile_instance.skills = ", ".join(new_skills_list)
                    messages.success(request, "Skills extracted from your resume!")
                else:
                    messages.warning(request, err)
            profile_instance.save()
            return redirect('recommendations')
    else:
        form = ProfileForm(instance=user_profile)
    return render(request, "profile.html", {'form': form, 'profile': user_profile})

@login_required
def recommendations(request):
    seed_internships_from_csv() 
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    skills_text = user_profile.skills
    results = []
    skill_gaps = []
    
    # Get filters
    location_query = request.GET.get('location', '')
    work_type_filter = request.GET.get('work_type', '')
    sort_by = request.GET.get('sort', 'match_percentage_desc') # Default sort by match percentage

    if user_profile and skills_text:
        internships_qs = Internship.objects.all()
        if location_query:
            internships_qs = internships_qs.filter(location__icontains=location_query)
        if work_type_filter:
            internships_qs = internships_qs.filter(work_type=work_type_filter)

        internships_df = pd.DataFrame(list(internships_qs.values(
            'id', 'title', 'company_name', 'location', 
            'skills_required', 'interest_area', 'education_level', 
            'stipend', 'duration', 'application_url', 'work_type'
        )))
        
        if not internships_df.empty:
            internships_df.rename(columns={
                'title': 'Title',
                'location': 'Location',
                'skills_required': 'Skills_Required',
                'interest_area': 'Interest_Area',
                'education_level': 'Education _Level',
                'stipend': 'Stipend',
                'duration': 'Duration'
            }, inplace=True)

            student_profile = {"Skills_ILE": skills_text}
            df = intern(student_profile, internships_df)
            
            def parse_skills(s):
                if pd.isna(s): return []
                items = re.split(r'[;,]', str(s))
                return [item.strip() for item in items if item.strip()]
            
            if not df.empty:
                df['Skills_List'] = df['Skills_Required'].apply(parse_skills)
                
                # Apply sorting
                if sort_by == 'stipend_asc':
                    df = df.sort_values(by='Stipend', ascending=True)
                elif sort_by == 'stipend_desc':
                    df = df.sort_values(by='Stipend', ascending=False)
                elif sort_by == 'match_percentage_asc':
                    df = df.sort_values(by='Match_Percentage', ascending=True)
                else: # Default to match_percentage_desc
                    df = df.sort_values(by='Match_Percentage', ascending=False)

                results = df.to_dict(orient="records")
            
            user_skills_list = [s.strip() for s in skills_text.split(",")]
            skill_gaps = analyze_skill_gaps(user_skills_list, results or [])

    saved_ids = []
    if request.user.is_authenticated:
        saved_ids = list(SavedInternship.objects.filter(user=request.user).values_list('internship_id', flat=True))

    return render(request, "recommendations.html", {
        "results": results,
        "skill_gaps": skill_gaps,
        "skills": skills_text,
        "saved_ids": saved_ids,
        "current_filters": {
            "location": location_query,
            "work_type": work_type_filter,
            "sort": sort_by
        }
    })

def all_internships(request):
    seed_internships_from_csv()
    
    # Get filters from request
    location_query = request.GET.get('location', '')
    work_type_filter = request.GET.get('work_type', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    internships = Internship.objects.all()
    
    if location_query:
        internships = internships.filter(location__icontains=location_query)
    
    if work_type_filter:
        internships = internships.filter(work_type=work_type_filter)
        
    # Sort
    if sort_by == 'stipend_asc':
        # Python sort because numeric_stipend is a property
        internships = sorted(internships, key=lambda i: i.numeric_stipend)
    elif sort_by == 'stipend_desc':
        internships = sorted(internships, key=lambda i: i.numeric_stipend, reverse=True)
    elif sort_by == 'created_at':
        internships = internships.order_by('created_at')
    else:
        internships = internships.order_by('-created_at')
    
    applied_ids = []
    saved_ids = []
    if request.user.is_authenticated:
        applied_ids = list(Application.objects.filter(user=request.user).values_list('internship_id', flat=True))
        saved_ids = list(SavedInternship.objects.filter(user=request.user).values_list('internship_id', flat=True))
        
    return render(request, "all_internships.html", {
        "internships": internships,
        "applied_ids": applied_ids,
        "saved_ids": saved_ids,
        "current_filters": {
            "location": location_query,
            "work_type": work_type_filter,
            "sort": sort_by
        }
    })

@login_required
def apply_internship(request, pk):
    internship = get_object_or_404(Internship, pk=pk)
    if not Application.objects.filter(user=request.user, internship=internship).exists():
        Application.objects.create(user=request.user, internship=internship)
        messages.success(request, f"Successfully applied for internship at {internship.company_name}!")
    else:
        messages.info(request, "You already marked this as applied.")
    
    # NEW: Redirect to the external application URL
    url = internship.application_url or "/external-apply-dummy/"
    if url.startswith('http'):
        return redirect(url)
    return redirect('external_apply_dummy')

@login_required
def application_history(request):
    applications = Application.objects.filter(user=request.user).order_by('-applied_at')
    return render(request, "application_history.html", {"applications": applications})

@csrf_protect
@user_passes_test(lambda u: u.is_staff)
def admin_dashboard(request):
    seed_internships_from_csv() # Ensure data is there
    users = User.objects.all().select_related('userprofile').order_by('-userprofile__last_activity')
    internships = Internship.objects.all().order_by('-id')
    applications_count = Application.objects.count()
    
    dataset_info = {
        'total_rows': 0,
        'last_modified': 'Unknown',
        'file_size': '0 KB',
        'path': DATA_PATH
    }
    
    if os.path.exists(DATA_PATH):
        try:
            stats = os.stat(DATA_PATH)
            # Use timezone to avoid import issues or just use standard datetime
            from django.utils import timezone
            dataset_info['total_rows'] = Internship.objects.count() # Use DB count as proxy or read CSV
            dataset_info['last_modified'] = timezone.datetime.fromtimestamp(stats.st_mtime).strftime('%b %d, %Y %H:%M')
            dataset_info['file_size'] = f"{stats.st_size / 1024:.1f} KB"
        except Exception:
            pass

    if request.method == "POST":
        form = InternshipForm(request.POST)
        if form.is_valid():
            new_internship = form.save()
            
            # Sync back to CSV dataset
            try:
                if os.path.exists(DATA_PATH):
                    df = pd.read_csv(DATA_PATH)
                    
                    # Ensure Company_Name exists in CSV structure
                    if 'Company_Name' not in df.columns:
                        cols = list(df.columns)
                        # Try to insert after Title column
                        title_col = next((c for c in cols if 'Title' in c), None)
                        idx = cols.index(title_col) + 1 if title_col else 1
                        df.insert(idx, 'Company_Name', '')
                    
                    # Calculate new No. index
                    try:
                        new_no = int(df['No.'].max()) + 1 if 'No.' in df.columns and not df.empty else 1
                    except:
                        new_no = len(df) + 1
                    
                    # Map Internship model fields to CSV columns
                    new_row_data = {}
                    for col in df.columns:
                        if col == 'No.': 
                            new_row_data[col] = new_no
                        elif 'Title' in col: 
                            new_row_data[col] = new_internship.title
                        elif 'Company_Name' in col: 
                            new_row_data[col] = (new_internship.company_name or "")
                        elif 'Skills' in col: 
                            new_row_data[col] = new_internship.skills_required
                        elif 'Location' in col: 
                            new_row_data[col] = new_internship.location
                        elif 'Interest' in col: 
                            new_row_data[col] = new_internship.interest_area
                        elif 'Education' in col: 
                            new_row_data[col] = new_internship.education_level
                        elif 'Stipend' in col: 
                            new_row_data[col] = new_internship.stipend
                        elif 'Duration' in col: 
                            new_row_data[col] = new_internship.duration
                        elif 'Application' in col or col == 'Application_URL':
                            new_row_data[col] = new_internship.application_url or "/external-apply-dummy/"
                        else:
                            new_row_data[col] = ""

                    # Use concat instead of append (deprecated)
                    df = pd.concat([df, pd.DataFrame([new_row_data])], ignore_index=True)
                    df.to_csv(DATA_PATH, index=False)
            except Exception as e:
                print(f"Error updating CSV: {e}")
                
            messages.success(request, "New entry saved to Database and CSV Dataset!")
            return redirect('admin_dashboard')
    else:
        form = InternshipForm()
        
    return render(request, "admin_dashboard.html", {
        "users": users,
        "internships": internships,
        "applications_count": applications_count,
        "dataset_info": dataset_info,
        "form": form
    })

def external_apply_dummy(request):
    return render(request, "external_apply_dummy.html")

@user_passes_test(lambda u: u.is_staff)
def sync_from_csv(request):
    seed_internships_from_csv()
    messages.success(request, "Database synchronized with CSV dataset.")
    return redirect('admin_dashboard')

def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('admin_dashboard')
        return redirect('recommendations')
    return redirect('all_internships')

@login_required
def saved_internships(request):
    saved = SavedInternship.objects.filter(user=request.user).select_related('internship')
    return render(request, "saved_internships.html", {"saved_items": saved})

@login_required
def toggle_save_internship(request, pk):
    internship = get_object_or_404(Internship, pk=pk)
    saved_item = SavedInternship.objects.filter(user=request.user, internship=internship)
    
    if saved_item.exists():
        saved_item.delete()
        messages.info(request, f"Removed {internship.title} from bookmarks.")
    else:
        SavedInternship.objects.create(user=request.user, internship=internship)
        messages.success(request, f"Added {internship.title} to bookmarks!")
    
    return redirect(request.META.get('HTTP_REFERER', 'all_internships'))

@login_required
def trends(request):
    # Get top 10 most applied internships
    from django.db.models import Count
    top_internships = Internship.objects.annotate(app_count=Count('applicants')).order_by('-app_count')[:10]
    
    labels = [i.title[:30] + '...' if len(i.title) > 30 else i.title for i in top_internships]
    data = [i.app_count for i in top_internships]
    
    # New Pie and Scatter Data
    pie_data = data
    scatter_data = [{"x": i.app_count, "y": i.numeric_stipend, "label": i.title[:20]} for i in top_internships]

    return render(request, "trends.html", {
        "labels": labels,
        "data": data,
        "pie_data": pie_data,
        "scatter_data": scatter_data,
        "top_internships": top_internships
    })