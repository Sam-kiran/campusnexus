# Login Module - CampusNexus System

## Overview
The Login Module is a comprehensive authentication system that handles user authentication, role-based access control, and integration with Supabase (optional). It supports three user roles: Student, Admin, and Organizer.

---

## 1. User Model (`users/models.py`)

### Custom User Model
The system uses Django's AbstractUser as the base and extends it with role-based functionality.

```python
class User(AbstractUser):
    """Custom User model with role-based access."""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True, validators=[EmailValidator(), validate_college_email])
    department = models.CharField(max_length=100, blank=True)
    student_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_verified = models.BooleanField(default=False)
```

### Key Features:
- **Role-based Access**: Three roles (Student, Admin, Organizer)
- **College Email Validation**: Only accepts emails from configured college domain
- **Email Verification**: Tracks if user email is verified
- **Student ID**: Unique identifier for students
- **Profile Management**: Supports profile pictures and department information

### Helper Methods:
- `is_student()`: Returns True if user is a student
- `is_admin()`: Returns True if user is an admin
- `is_organizer()`: Returns True if user is an organizer
- `is_admin_or_organizer()`: Returns True if user has admin or organizer role

---

## 2. Login View (`users/views.py`)

### Login Functionality
The login view supports both Django authentication and optional Supabase integration.

```python
@require_http_methods(["GET", "POST"])
def login_view(request):
    """Login view with optional Supabase integration."""
    if request.user.is_authenticated:
        return redirect('users:home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'student')
        
        # Try Supabase if configured, otherwise use Django auth
        if settings.SUPABASE_URL:
            # Validate with Supabase
            supabase_user = validate_supabase_auth(email, password)
            
            if supabase_user:
                try:
                    # Get Django user
                    user = User.objects.get(email=email)
                    if user.role != role:
                        messages.error(request, 'Invalid role for this account.')
                        return render(request, 'users/login.html')
                    
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    if user.is_student():
                        return redirect('dashboard:student_dashboard')
                    else:
                        return redirect('dashboard:admin_dashboard')
                except User.DoesNotExist:
                    messages.error(request, 'User not found. Please sign up first.')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            # Use Django's built-in authentication
            try:
                user = User.objects.get(email=email)
                if user.role != role:
                    messages.error(request, 'Invalid role for this account.')
                    return render(request, 'users/login.html')
                
                # Check password using Django's authentication
                if user.check_password(password):
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    if user.is_student():
                        return redirect('dashboard:student_dashboard')
                    else:
                        return redirect('dashboard:admin_dashboard')
                else:
                    messages.error(request, 'Invalid email or password.')
            except User.DoesNotExist:
                messages.error(request, 'User not found. Please sign up first.')
    
    return render(request, 'users/login.html')
```

### Login Process Flow:
1. **Check Authentication**: Redirects authenticated users to home
2. **Collect Credentials**: Email, password, and role from form
3. **Authentication Method**:
   - If Supabase is configured: Validates with Supabase first
   - Otherwise: Uses Django's built-in authentication
4. **Role Validation**: Verifies selected role matches user's role
5. **Redirect**: Based on user role:
   - Students → Student Dashboard
   - Admin/Organizer → Admin Dashboard

---

## 3. Login Template (`templates/users/login.html`)

### HTML Form Structure
```html
{% extends 'base.html' %}

{% block title %}Login - CampusNexus{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-5">
        <div class="card">
            <div class="card-header text-center">
                <h3>Login to CampusNexus</h3>
            </div>
            <div class="card-body">
                <form method="post">
                    {% csrf_token %}
                    <div class="mb-3">
                        <label for="email" class="form-label">Email</label>
                        <input type="email" class="form-control" id="email" name="email" required>
                    </div>
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" required>
                    </div>
                    <div class="mb-3">
                        <label for="role" class="form-label">Role</label>
                        <select class="form-select" id="role" name="role" required>
                            <option value="student">Student</option>
                            <option value="admin">Admin</option>
                            <option value="organizer">Organizer</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Login</button>
                </form>
                <div class="text-center mt-3">
                    <p><a href="{% url 'users:password_reset' %}">Forgot Password?</a></p>
                    <p>Don't have an account? <a href="{% url 'users:signup' %}">Sign up</a></p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Form Fields:
1. **Email**: Required email input field
2. **Password**: Required password input field (hidden)
3. **Role**: Dropdown selection (Student, Admin, Organizer)
4. **CSRF Token**: Django security token for form submission

### Additional Links:
- Password Reset Link
- Sign Up Link

---

## 4. Authentication Utilities (`users/utils.py`)

### Supabase Integration Functions

#### Get Supabase Client
```python
def get_supabase_client():
    """Get Supabase client instance."""
    if not SUPABASE_AVAILABLE:
        return None
    try:
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return supabase
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        return None
```

#### Validate Supabase Authentication
```python
def validate_supabase_auth(email: str, password: str) -> dict:
    """Validate user credentials with Supabase."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user:
            return response.user
        return None
    except Exception as e:
        logger.error(f"Supabase auth error: {e}")
        return None
```

#### Create Supabase User
```python
def create_supabase_user(email: str, password: str) -> dict:
    """Create a new user in Supabase."""
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None
        
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            return response.user
        return None
    except Exception as e:
        logger.error(f"Supabase signup error: {e}")
        return None
```

---

## 5. URL Routing (`users/urls.py`)

### URL Patterns
```python
app_name = 'users'

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('api/check-email/', views.check_email, name='check_email'),
    
    # Password reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(...), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(...), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(...), name='password_reset_complete'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
]
```

### Available Endpoints:
- `/` - Home (redirects based on role)
- `/login/` - Login page
- `/signup/` - Registration page
- `/logout/` - Logout functionality
- `/password-reset/` - Password reset request
- `/verify-email/` - Email verification
- `/api/check-email/` - API endpoint to check email availability

---

## 6. Security Features

### 1. College Email Validation
- Only accepts emails from configured college domain
- Validated at both model and form level

### 2. CSRF Protection
- All forms include Django's CSRF token
- Prevents cross-site request forgery attacks

### 3. Password Security
- Passwords are hashed using Django's password hashing
- Never stored in plain text

### 4. Role-based Access Control
- Users must select correct role during login
- Role validation prevents unauthorized access

### 5. Session Management
- Django's built-in session framework
- Secure session cookies

---

## 7. Additional Features

### Home View
```python
def home(request):
    """Home page - redirects based on user role."""
    if request.user.is_authenticated:
        if request.user.is_student():
            return redirect('dashboard:student_dashboard')
        elif request.user.is_admin_or_organizer():
            return redirect('dashboard:admin_dashboard')
    return redirect('users:login')
```

### Logout View
```python
@login_required
def logout_view(request):
    """Logout view."""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('users:login')
```

### Email Verification API
```python
@api_view(['GET'])
@permission_classes([AllowAny])
def check_email(request):
    """API endpoint to check if email exists."""
    email = request.GET.get('email')
    if email:
        exists = User.objects.filter(email=email).exists()
        return Response({'exists': exists})
    return Response({'error': 'Email required'}, status=status.HTTP_400_BAD_REQUEST)
```

---

## 8. System Architecture

### Authentication Flow Diagram

```
User Input (Login Form)
    ↓
[Login View]
    ↓
Check Authentication Status
    ↓
Collect Credentials (Email, Password, Role)
    ↓
┌─────────────────────────────────────┐
│  Authentication Method Selection    │
└─────────────────────────────────────┘
    ↓
┌─────────────┐              ┌─────────────┐
│  Supabase   │              │   Django    │
│     Auth    │              │     Auth    │
└─────────────┘              └─────────────┘
    ↓                              ↓
Validate Credentials        Check Password
    ↓                              ↓
    └──────────────┬───────────────┘
                   ↓
            Role Validation
                   ↓
            Session Creation
                   ↓
            Role-based Redirect
                   ↓
    ┌──────────────┴───────────────┐
    ↓                              ↓
Student Dashboard         Admin/Organizer Dashboard
```

---

## 9. Error Handling

### Common Error Messages:
- "Invalid email or password." - Authentication failed
- "Invalid role for this account." - Role mismatch
- "User not found. Please sign up first." - User doesn't exist
- "Email must be from {domain} domain." - Invalid email domain

### Error Handling Strategy:
- User-friendly error messages
- Secure error responses (don't reveal user existence)
- Proper exception handling
- Logging for debugging

---

## 10. Dependencies

### Required Packages:
- Django (Web framework)
- Django REST Framework (API endpoints)
- Supabase Python Client (Optional, for Supabase integration)

### Settings Configuration:
```python
# Required settings
COLLEGE_EMAIL_DOMAIN = '@yourcollege.edu'  # Configure in settings.py

# Optional Supabase settings
SUPABASE_URL = 'your-supabase-url'  # Optional
SUPABASE_KEY = 'your-supabase-key'  # Optional
```

---

## 11. Testing Considerations

### Test Cases to Consider:
1. Valid login with correct credentials
2. Invalid email/password combination
3. Role mismatch scenario
4. Non-existent user login attempt
5. Supabase authentication (if enabled)
6. Django authentication fallback
7. Email validation
8. CSRF protection
9. Session management
10. Redirect behavior based on roles

---

## Conclusion

The Login Module provides a robust, secure authentication system with:
- ✅ Role-based access control
- ✅ Dual authentication support (Django + Supabase)
- ✅ College email validation
- ✅ Secure password handling
- ✅ Session management
- ✅ Error handling and user feedback
- ✅ Password reset functionality
- ✅ Email verification support

This module serves as the foundation for secure access to the CampusNexus platform, ensuring only authorized users with valid college email addresses can access the system.



