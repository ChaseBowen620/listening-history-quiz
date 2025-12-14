# Deployment Guide for Spotify Quiz App

This guide covers deploying your Flask app to platforms that provide HTTPS URLs for Spotify OAuth.

## Option 1: Render (Recommended - Easiest for Flask) ⭐

Render provides free HTTPS URLs and is perfect for Flask apps.

**⚠️ Important:** Spotify doesn't allow callback URLs to contain the brand name "spotify". Make sure your service name (and thus URL) doesn't include "spotify" in it. For example, use `listening-history-quiz` instead of `spotify-quiz-app`.

### Steps:

1. **Sign up at [render.com](https://render.com)** (free tier available)

2. **Create a new Web Service:**
   - Connect your GitHub repository
   - Or use the Render dashboard to deploy

3. **Configure the service:**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn --bind 0.0.0.0:$PORT src.app:app`
   - **Environment:** Python 3

4. **Set Environment Variables:**
   - `SPOTIFY_CLIENT_ID` - Your Spotify Client ID
   - `SPOTIFY_CLIENT_SECRET` - Your Spotify Client Secret
   - `SPOTIFY_REDIRECT_URI` - Will be `https://your-app-name.onrender.com/callback`
   - `FLASK_ENV` - Set to `production`

5. **Update Spotify App Settings:**
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Add `https://your-app-name.onrender.com/callback` to Redirect URIs

6. **Deploy!** Render will give you a URL like `https://listening-history-quiz.onrender.com`

---

## Option 2: Vercel

Vercel works but requires Flask to run as serverless functions.

### Steps:

1. **Install Vercel CLI:**
   ```bash
   npm i -g vercel
   ```

2. **Deploy:**
   ```bash
   cd listening-history-quiz
   vercel
   ```

3. **Set Environment Variables in Vercel Dashboard:**
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REDIRECT_URI` - Will be `https://your-app.vercel.app/callback`

4. **Update Spotify App Settings:**
   - Add `https://your-app.vercel.app/callback` to Redirect URIs

**Note:** Vercel uses serverless functions, so sessions might need Redis/MongoDB for production. For development, it should work fine.

---

## Option 3: Railway

Railway is another great option with a free tier.

### Steps:

1. **Sign up at [railway.app](https://railway.app)**

2. **Create a new project** and connect your GitHub repo

3. **Railway will auto-detect Python:**
   - It will use `requirements.txt` automatically
   - You may need to add a `Procfile`:
     ```
     web: gunicorn --bind 0.0.0.0:$PORT src.app:app
     ```

4. **Set Environment Variables:**
   - `SPOTIFY_CLIENT_ID`
   - `SPOTIFY_CLIENT_SECRET`
   - `SPOTIFY_REDIRECT_URI` - Will be `https://your-app.up.railway.app/callback`

5. **Update Spotify App Settings:**
   - Add the Railway URL to Redirect URIs

---

## Option 4: Fly.io

Fly.io is excellent for Flask apps.

### Steps:

1. **Install Fly CLI:**
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Create `fly.toml`:**
   ```toml
   app = "your-app-name"
   primary_region = "iad"

   [build]

   [http_service]
     internal_port = 3000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
     min_machines_running = 0
     processes = ["app"]

   [[vm]]
     memory_mb = 256
   ```

3. **Deploy:**
   ```bash
   fly launch
   fly secrets set SPOTIFY_CLIENT_ID=your_id
   fly secrets set SPOTIFY_CLIENT_SECRET=your_secret
   fly secrets set SPOTIFY_REDIRECT_URI=https://your-app.fly.dev/callback
   ```

---

## Quick Fix: ngrok (For Local Development/Testing)

If you just need to test quickly without deploying:

1. **Install ngrok:**
   ```bash
   # Download from https://ngrok.com/download
   # Or: brew install ngrok (Mac) / apt install ngrok (Linux)
   ```

2. **Start your Flask app:**
   ```bash
   python src/app.py
   ```

3. **In another terminal, start ngrok:**
   ```bash
   ngrok http 3000
   ```

4. **Use the HTTPS URL ngrok provides:**
   - Example: `https://abc123.ngrok.io/callback`
   - Add this to your Spotify app's Redirect URIs
   - Update `SPOTIFY_REDIRECT_URI` in your `.env` file

**Note:** ngrok URLs change each time you restart (unless you have a paid plan), so this is only for testing.

---

## Important Notes:

1. **Session Storage:** For production on serverless platforms (like Vercel), consider using:
   - Redis (for session storage)
   - Or Flask-Session with a database
   - Or JWT tokens instead of server-side sessions

2. **Secret Key:** In production, use a fixed secret key, not `secrets.token_hex(16)`:
   ```python
   app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))
   ```

3. **CORS:** If you're using a separate frontend, you may need to configure CORS.

4. **Environment Variables:** Never commit `.env` files. Always use platform-specific environment variable settings.

---

## Recommended: Render

For your Flask app, **Render is the easiest option** because:
- ✅ Free tier with HTTPS
- ✅ No serverless conversion needed
- ✅ Simple deployment
- ✅ Automatic SSL certificates
- ✅ Easy environment variable management

Just connect your repo, set environment variables, and deploy!

