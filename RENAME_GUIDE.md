# How to Rename Your Project and Render URL

Since Spotify doesn't allow callback URLs to contain the brand name "spotify", here's how to rename everything:

## Step 1: Rename the Render Service

1. **Go to your Render Dashboard**
2. **Click on your service** (currently named `spotify-quiz-app`)
3. **Go to Settings** (in the left sidebar)
4. **Find "Name" field** and change it to: `listening-history-quiz` (or any name you prefer that doesn't contain "spotify")
5. **Save the changes**

Render will automatically update the URL to match the new name:
- Old: `https://spotify-quiz-app.onrender.com`
- New: `https://listening-history-quiz.onrender.com`

## Step 2: Update Environment Variables

1. **Still in Render Settings**, go to **Environment** section
2. **Update `SPOTIFY_REDIRECT_URI`** to:
   ```
   https://listening-history-quiz.onrender.com/callback
   ```
   (Replace `listening-history-quiz` with whatever name you chose)

## Step 3: Update Spotify App Settings

1. **Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)**
2. **Click on your app**
3. **Go to "Edit Settings"**
4. **In "Redirect URIs"**, remove the old URL and add:
   ```
   https://listening-history-quiz.onrender.com/callback
   ```
5. **Click "Add"** and **Save**

## Step 4: Redeploy (if needed)

Render should automatically redeploy when you change the service name, but if the URL doesn't update immediately:
1. Go to **Manual Deploy** in Render
2. Click **Deploy latest commit**

## Alternative Names (if you want something different)

Here are some Spotify-compliant name suggestions:
- `listening-history-quiz` (current)
- `music-quiz-app`
- `music-personality-quiz`
- `my-music-quiz`
- `music-taste-quiz`
- `listening-habits-quiz`
- `music-discovery-quiz`
- `your-music-profile`

Just make sure whatever you choose:
- ✅ Doesn't contain "spotify"
- ✅ Is available on Render (they'll tell you if it's taken)
- ✅ Is easy to remember

## Verify Everything Works

After renaming:
1. Visit your new URL: `https://listening-history-quiz.onrender.com`
2. Try logging in with Spotify
3. The OAuth callback should work now!

---

**Note:** The project files have been updated to use `listening-history-quiz` as the default name, but you can choose any name you like as long as it doesn't contain "spotify".

