import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
# Use environment variable for secret key in production, or generate one for development
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Spotify configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Spotify OAuth scope
SCOPE = "user-read-recently-played user-top-read user-read-private user-read-email"

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
        redirect_uri=SPOTIFY_REDIRECT_URI,
        scope=SCOPE
    )

@app.route('/')
def index():
    """Home page with quiz introduction"""
    return render_template('index.html')

@app.route('/login')
def login():
    """Initiate Spotify OAuth login"""
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Handle Spotify OAuth callback"""
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    session['token_info'] = token_info
    return redirect(url_for('quiz'))

@app.route('/quiz')
def quiz():
    """Main quiz page"""
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # Get user info
    user = sp.current_user()
    session['user_id'] = user['id']
    session['user_name'] = user['display_name']
    
    return render_template('quiz.html', user_name=user['display_name'])

@app.route('/api/quiz-data')
def get_quiz_data():
    """Get Spotify data for quiz questions"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    try:
        # Get user's top tracks and artists
        top_tracks = sp.current_user_top_tracks(limit=20, time_range='medium_term')
        top_artists = sp.current_user_top_artists(limit=20, time_range='medium_term')
        recent_tracks = sp.current_user_recently_played(limit=20)
        
        # Get user's playlists
        playlists = sp.current_user_playlists(limit=20)
        
        quiz_data = {
            'top_tracks': top_tracks['items'],
            'top_artists': top_artists['items'],
            'recent_tracks': [item['track'] for item in recent_tracks['items']],
            'playlists': playlists['items']
        }
        
        return jsonify(quiz_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/results')
def results():
    """Display quiz results"""
    if 'quiz_results' not in session:
        return redirect(url_for('quiz'))
    
    results = session['quiz_results']
    return render_template('results.html', results=results)

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    """Process quiz answers and calculate results"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    answers = request.json
    token_info = session['token_info']
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    try:
        # Calculate results based on answers
        results = calculate_quiz_results(answers, sp)
        session['quiz_results'] = results
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_quiz_results(answers, sp):
    """Calculate personalized results based on quiz answers"""
    results = {
        'listening_personality': '',
        'music_taste': '',
        'discovery_style': '',
        'mood_patterns': '',
        'recommendations': []
    }
    
    # Analyze answers and generate results
    # This is a simplified version - you can expand this logic
    
    if answers.get('listening_frequency') == 'daily':
        results['listening_personality'] = 'Music Enthusiast'
    elif answers.get('listening_frequency') == 'weekly':
        results['listening_personality'] = 'Casual Listener'
    else:
        results['listening_personality'] = 'Selective Listener'
    
    # Get some recommendations based on user's top artists
    top_artists = sp.current_user_top_artists(limit=5)
    if top_artists['items']:
        # Get recommendations based on top artist
        seed_artist = top_artists['items'][0]['id']
        recommendations = sp.recommendations(seed_artists=[seed_artist], limit=5)
        results['recommendations'] = recommendations['tracks']
    
    return results

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)

