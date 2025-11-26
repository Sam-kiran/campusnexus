# OpenAI API Key Configuration Guide

## ✅ Current Status
Your OpenAI API key is **already configured** and working! The key has been set up in your `.env` file.

## 📝 How It Works

The project reads the OpenAI API key from the `.env` file located in the project root:
```
C:\Users\saman\OneDrive\Desktop\Mini Project\CampusNexus\.env
```

The key is loaded automatically when Django starts via the `python-dotenv` package.

## 🔑 Getting a New OpenAI API Key (If Needed)

If you need to get a new API key or update the existing one:

### Step 1: Sign Up / Log In to OpenAI
1. Go to [https://platform.openai.com](https://platform.openai.com)
2. Sign up for an account or log in if you already have one

### Step 2: Create an API Key
1. Once logged in, click on your profile icon (top right)
2. Select **"API keys"** from the dropdown menu
3. Click **"Create new secret key"**
4. Give it a name (e.g., "CampusNexus Project")
5. Click **"Create secret key"**
6. **IMPORTANT**: Copy the key immediately - you won't be able to see it again!

### Step 3: Add the Key to Your .env File

Open the `.env` file in your project root and add/update the line:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

**Important Notes:**
- ❌ **DO NOT** include spaces around the `=` sign
- ❌ **DO NOT** wrap the key in quotes
- ✅ Format: `OPENAI_API_KEY=sk-...`
- ✅ Keep this file **SECRET** - never commit it to Git!

### Step 4: Restart Your Django Server

After updating the `.env` file:
1. Stop your Django server (Ctrl+C)
2. Restart it: `python manage.py runserver`

## 🎯 What the API Key Enables

With the OpenAI API key configured, you can use:

1. **AI Banner Generation** - Automatically generate event banners using DALL-E 3
   - Available in Event Create/Edit forms
   - Check "Generate AI Banner & Poster" option

2. **AI Event Creation** - Generate event details using ChatGPT
   - Available through the chatbot interface

3. **Other AI Features** - Any future AI-powered features in the application

## 🔒 Security Best Practices

1. **Never commit `.env` to Git** - It should already be in `.gitignore`
2. **Don't share your API key** - Treat it like a password
3. **Rotate keys periodically** - If you suspect a key is compromised, create a new one
4. **Monitor usage** - Check your OpenAI dashboard for usage and costs

## 🧪 Testing the Configuration

To verify your API key is working:

1. **Check if Django reads it:**
   ```python
   python manage.py shell
   >>> from django.conf import settings
   >>> print("Key configured:", bool(settings.OPENAI_API_KEY))
   ```

2. **Test AI Banner Generation:**
   - Go to Event Create/Edit page
   - Check "Generate AI Banner & Poster"
   - Create/Update an event
   - The banner should be generated automatically

## ⚠️ Troubleshooting

### Issue: "OpenAI API key not configured"
- **Solution**: Make sure your `.env` file is in the project root
- **Solution**: Check the format: `OPENAI_API_KEY=sk-...` (no spaces, no quotes)

### Issue: "OpenAI library not available"
- **Solution**: Install OpenAI: `pip install openai`
- **Solution**: Make sure you're in the virtual environment

### Issue: "Billing hard limit has been reached" or "Billing limit reached"
This is the most common issue! It means your OpenAI account has reached its spending limit.

**Solutions:**
1. **Add a payment method:**
   - Go to [https://platform.openai.com/account/billing](https://platform.openai.com/account/billing)
   - Click "Add payment method"
   - Add a credit card or other payment method

2. **Increase your spending limit:**
   - Go to [https://platform.openai.com/account/billing/limits](https://platform.openai.com/account/billing/limits)
   - Increase your "Hard limit" or "Soft limit"
   - The hard limit is the maximum you're willing to spend per month

3. **Check your usage:**
   - Go to [https://platform.openai.com/usage](https://platform.openai.com/usage)
   - See how much you've used and what your limits are

**Note:** OpenAI requires a payment method for DALL-E 3 image generation, even if you have free credits.

### Issue: API errors or rate limits
- **Solution**: Check your OpenAI account for usage limits
- **Solution**: Verify you have credits/billing set up on OpenAI
- **Solution**: Wait a few minutes and try again if you hit rate limits

## 📚 Additional Resources

- [OpenAI Platform Documentation](https://platform.openai.com/docs)
- [OpenAI API Pricing](https://openai.com/pricing)
- [DALL-E 3 Documentation](https://platform.openai.com/docs/guides/images)

---

**Your API key is currently configured and ready to use!** 🎉

