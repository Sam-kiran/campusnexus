# Vercel Deployment Guide for CampusNexus

## 🚀 Complete Step-by-Step Guide (Beginner Friendly)

This guide will help you deploy your CampusNexus Django project to Vercel.

---

## Part 1: Prepare Your Project for Vercel

### Step 1: Create Required Files

#### A. Create `vercel.json` in the root folder

Create a new file called `vercel.json` in the main project folder (same location as `manage.py`) and paste this:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "campusnexus/wsgi.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "15mb", "runtime": "python3.9" }
    },
    {
      "src": "build_files.sh",
      "use": "@vercel/static-build",
      "config": {
        "distDir": "staticfiles"
      }
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "campusnexus/wsgi.py"
    }
  ]
}
```

#### B. Update `build_files.sh`

Open the `build_files.sh` file and make sure it contains:

```bash
#!/bin/bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
```

#### C. Create `vercel_wsgi.py`

Create a new file called `vercel_wsgi.py` in the `campusnexus` folder (where `settings.py` is located):

```python
from .wsgi import application
app = application
```

---

### Step 2: Update Django Settings

Open `campusnexus/settings.py` and make these changes:

#### A. Update ALLOWED_HOSTS (around line 28):
```python
ALLOWED_HOSTS = ['*']  # For now, allow all hosts
```

#### B. Update DATABASES (around line 80):
```python
# For Vercel, use SQLite or switch to PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/tmp/db.sqlite3',  # Vercel uses /tmp for temporary storage
    }
}
```

**⚠️ IMPORTANT NOTE**: SQLite on Vercel is temporary and resets on each deployment. For production, you should use a proper database like PostgreSQL (see Section at the end).

#### C. Update STATIC settings (around line 120):
```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
```

#### D. Add CSRF settings (add after STATIC settings):
```python
CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'https://your-custom-domain.com'  # Add your custom domain if you have one
]
```

---

### Step 3: Update Requirements

Make sure your `requirements.txt` has all needed packages. Key ones for Vercel:

```
Django>=4.2.0
gunicorn
whitenoise
psycopg2-binary  # If using PostgreSQL
python-dotenv
```

---

## Part 2: Deploy to Vercel

### Step 1: Create Vercel Account

1. Go to [https://vercel.com](https://vercel.com)
2. Click "Sign Up" button (top right)
3. Choose "Continue with GitHub"
4. Log in with your GitHub account
5. Authorize Vercel to access your GitHub

### Step 2: Import Your Project

1. Once logged in, click **"Add New..."** button (top right)
2. Select **"Project"**
3. You'll see a list of your GitHub repositories
4. Find **"campusnexus"** repository
5. Click **"Import"** button next to it

### Step 3: Configure Project Settings

You'll now see the "Configure Project" page:

1. **Project Name**: Leave as `campusnexus` or change it
2. **Framework Preset**: Select "Other" (not Django, we're using custom config)
3. **Root Directory**: Leave as `./` (root)
4. **Build Command**: Leave empty (we use vercel.json)
5. **Output Directory**: Leave empty

### Step 4: Add Environment Variables

Click on **"Environment Variables"** section and add these:

1. **SECRET_KEY**
   - Name: `SECRET_KEY`
   - Value: `your-django-secret-key-here-make-it-long-and-random`
   - (To generate a new one: open Python and run `from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`)

2. **DEBUG**
   - Name: `DEBUG`
   - Value: `False`

3. **ALLOWED_HOSTS** (optional, we set to * in settings)
   - Name: `ALLOWED_HOSTS`
   - Value: `.vercel.app`

4. Add any other API keys you're using:
   - `OPENAI_API_KEY`
   - `EMAIL_HOST_USER`
   - `EMAIL_HOST_PASSWORD`
   - etc.

### Step 5: Deploy!

1. Click the big blue **"Deploy"** button
2. Wait for the build process (takes 2-5 minutes)
3. You'll see:
   - 🔨 Building...
   - ✅ Build completed
   - 🚀 Deploying...
   - ✅ Deployment successful

### Step 6: Access Your Site

1. Once deployment completes, you'll see **"Congratulations!"**
2. Click **"Visit"** button to see your live site
3. Your URL will be something like: `https://campusnexus-xyz123.vercel.app`

---

## Part 3: Post-Deployment Tasks

### Create Superuser (Admin Account)

Vercel doesn't provide shell access easily, so you have two options:

**Option A: Use Local Setup Then Switch to Cloud Database**
1. Set up PostgreSQL database (see below)
2. Create superuser locally: `python manage.py createsuperuser`
3. Your database will sync to Vercel

**Option B: Create Superuser Endpoint** (Quick & Dirty - Remove After Use!)
1. Add this temporarily to your `users/views.py`:

```python
from django.contrib.auth import get_user_model
from django.http import JsonResponse

def create_admin_once(request):
    User = get_user_model()
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'your-secure-password')
        return JsonResponse({'status': 'Admin created'})
    return JsonResponse({'status': 'Admin already exists'})
```

2. Add to `users/urls.py`:
```python
path('create-admin-secret/', views.create_admin_once, name='create_admin'),
```

3. Visit: `https://your-app.vercel.app/users/create-admin-secret/`
4. **REMOVE THIS CODE IMMEDIATELY AFTER USE!**

---

## Part 4: Set Up Proper Database (IMPORTANT!)

SQLite won't work properly on Vercel (it resets). Use PostgreSQL:

### Option 1: Vercel Postgres (Easiest)

1. In Vercel Dashboard, go to your project
2. Click **"Storage"** tab
3. Click **"Create Database"**
4. Select **"Postgres"**
5. Click **"Continue"**
6. Vercel will automatically add database environment variables
7. Update your `settings.py`:

```python
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DATABASE'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': '5432',
    }
}
```

### Option 2: Free External PostgreSQL (Supabase)

1. Go to [https://supabase.com](https://supabase.com)
2. Sign up and create a new project
3. Get your database credentials from **Settings > Database**
4. Add to Vercel environment variables:
   - `DATABASE_URL`: (the connection string from Supabase)

5. Update `settings.py`:
```python
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(default=os.environ.get('DATABASE_URL'))
}
```

6. Add to `requirements.txt`:
```
dj-database-url
psycopg2-binary
```

---

## Part 5: Common Issues & Solutions

### Issue 1: Static Files Not Loading
**Solution**: Make sure `whitenoise` is in requirements.txt and middleware

### Issue 2: CSRF Verification Failed
**Solution**: Add your Vercel domain to `CSRF_TRUSTED_ORIGINS` in settings.py

### Issue 3: Database Resets Every Deploy
**Solution**: Switch from SQLite to PostgreSQL (see Part 4)

### Issue 4: Build Fails
**Solution**: Check build logs in Vercel dashboard, usually missing dependencies in requirements.txt

### Issue 5: 500 Internal Server Error
**Solution**: 
1. Check Vercel function logs (Dashboard > Your Project > Functions tab)
2. Make sure DEBUG=False in production
3. Check all environment variables are set

---

## Part 6: Updating Your Deployed Site

Whenever you make changes to your code:

1. Commit changes to GitHub:
   ```bash
   git add .
   git commit -m "Your change description"
   git push origin main
   ```

2. Vercel automatically detects the push and redeploys (takes 2-3 minutes)
3. That's it! Your changes are live

---

## Part 7: Custom Domain (Optional)

### Add Your Own Domain

1. Buy a domain from Namecheap, GoDaddy, etc.
2. In Vercel Dashboard, go to your project
3. Click **"Settings"** > **"Domains"**
4. Click **"Add Domain"**
5. Enter your domain name
6. Follow Vercel's instructions to update DNS records
7. Wait 24-48 hours for DNS propagation

---

## 🎉 Congratulations!

Your CampusNexus project is now live on the internet!

**Next Steps:**
- ✅ Test all features on the live site
- ✅ Create admin account
- ✅ Set up proper database (PostgreSQL)
- ✅ Test registration and login
- ✅ Test event creation and payment flows
- ✅ Share the URL with your users!

---

## 📞 Quick Reference

- **Vercel Dashboard**: [https://vercel.com/dashboard](https://vercel.com/dashboard)
- **View Logs**: Dashboard > Your Project > Functions > Click on any function
- **Environment Variables**: Dashboard > Your Project > Settings > Environment Variables
- **Redeploy**: Dashboard > Your Project > Deployments > Click ⋯ > Redeploy

---

## 💡 Tips for Success

1. **Always test locally first** before pushing to GitHub
2. **Keep your SECRET_KEY secret** - never commit it to GitHub
3. **Use environment variables** for all sensitive data
4. **Monitor your logs** in Vercel dashboard after deployment
5. **Start with free tier** - upgrade only if needed
6. **Backup your database regularly** if using PostgreSQL

---

Good luck with your deployment! 🚀
