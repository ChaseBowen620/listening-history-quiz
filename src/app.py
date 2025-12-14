import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from .models import db, User, Album, SavedTrack, Playlist, TopTrack, TopArtist
from .spotify_data import sync_user_spotify_data
from .question_generator import generate_questions

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='../templates', static_folder='../static')
# Use environment variable for secret key in production, or generate one for development
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Database configuration
database_url = os.getenv('DATABASE_URL')
if not database_url:
    # Default to SQLite for local development
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'spotify_quiz.db')
    database_url = f'sqlite:///{db_path}'
elif database_url.startswith('postgres://'):
    # Handle Render's postgres:// URL format (needs postgresql://)
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Spotify configuration
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
SPOTIFY_REDIRECT_URI = os.getenv('SPOTIFY_REDIRECT_URI')

# Spotify OAuth scope - added user-library-read for saved albums and tracks
SCOPE = "user-read-recently-played user-top-read user-read-private user-read-email user-library-read"

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
    try:
        sp_oauth = create_spotify_oauth()
        session.clear()
        
        # Check if we have the authorization code
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            return f"Error from Spotify: {error}", 400
        
        if not code:
            return "No authorization code provided", 400
        
        # Exchange code for access token
        token_info = sp_oauth.get_access_token(code)
        
        if not token_info:
            return "Failed to get access token", 400
        
        # Store token in session
        session['token_info'] = token_info
        
        # Create Spotify client and get user info
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user = sp.current_user()
        user_id = user['id']
        session['user_id'] = user_id
        session['user_name'] = user.get('display_name', 'User')
        
        # Fetch and store all Spotify data in database
        try:
            sync_user_spotify_data(sp, user_id, user)
            session['data_synced'] = True
        except Exception as sync_error:
            print(f"Error syncing data: {str(sync_error)}")
            session['data_synced'] = False
            # Continue anyway - user can still use the app
        
        # Redirect to quiz page
        return redirect(url_for('quiz'))
    
    except Exception as e:
        # Log the error for debugging
        print(f"Callback error: {str(e)}")
        return f"An error occurred during authentication: {str(e)}", 500

@app.route('/quiz')
def quiz():
    """Main quiz page"""
    if 'token_info' not in session:
        return redirect(url_for('login'))
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'User')
    
    # Check if data was synced
    data_synced = session.get('data_synced', False)
    
    return render_template('quiz.html', user_name=user_name, data_synced=data_synced)

@app.route('/api/quiz-questions', methods=['GET', 'POST'])
def get_quiz_questions():
    """Generate or retrieve ChatGPT-generated quiz questions"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    try:
        # Generate questions using ChatGPT
        questions = generate_questions(user_id)
        
        # Store questions in session for grading
        session['quiz_questions'] = questions
        
        return jsonify({
            'success': True,
            'questions': questions
        })
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        return jsonify({'error': f'Failed to generate questions: {str(e)}'}), 500

@app.route('/api/quiz-data')
def get_quiz_data():
    """Get Spotify data from database (for reference, if needed)"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    try:
        # Get data from database
        albums = [album.to_dict() for album in Album.query.filter_by(user_id=user_id).all()]
        saved_tracks = [track.to_dict() for track in SavedTrack.query.filter_by(user_id=user_id).all()]
        playlists = [playlist.to_dict() for playlist in Playlist.query.filter_by(user_id=user_id).all()]
        
        # Get top tracks and artists for medium_term
        top_tracks = [track.to_dict() for track in TopTrack.query.filter_by(
            user_id=user_id, 
            time_range='medium_term'
        ).order_by(TopTrack.rank).all()]
        
        top_artists = [artist.to_dict() for artist in TopArtist.query.filter_by(
            user_id=user_id,
            time_range='medium_term'
        ).order_by(TopArtist.rank).all()]
        
        quiz_data = {
            'albums': albums,
            'saved_tracks': saved_tracks,
            'playlists': playlists,
            'top_tracks': top_tracks,
            'top_artists': top_artists
        }
        
        return jsonify(quiz_data)
    
    except Exception as e:
        print(f"Error getting quiz data: {str(e)}")
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
    questions = session.get('quiz_questions', [])
    
    if not questions:
        return jsonify({'error': 'No questions found'}), 400
    
    try:
        # Calculate results based on answers
        results = calculate_quiz_results(answers, questions)
        session['quiz_results'] = results
        return jsonify(results)
    
    except Exception as e:
        print(f"Error calculating results: {str(e)}")
        return jsonify({'error': str(e)}), 500

def calculate_quiz_results(answers, questions):
    """Calculate quiz results based on user answers"""
    correct_count = 0
    total_questions = len(questions)
    question_results = []
    
    for question in questions:
        question_id = question['id']
        user_answer = answers.get(question_id, '')
        correct_answer = question.get('correct_answer', '')
        
        # Compare answers (handle different question types)
        is_correct = False
        if question['type'] == 'drag_drop':
            # For drag-drop, compare order
            user_order = user_answer if isinstance(user_answer, list) else []
            # Parse correct_answer if it's a string representation of a list
            if isinstance(correct_answer, str) and correct_answer.startswith('['):
                import json
                try:
                    correct_order = json.loads(correct_answer)
                except:
                    correct_order = question.get('data', {}).get('correct_order', [])
            else:
                correct_order = correct_answer if isinstance(correct_answer, list) else question.get('data', {}).get('correct_order', [])
            is_correct = user_order == correct_order
        elif question['type'] == 'true_false':
            is_correct = str(user_answer).lower() == str(correct_answer).lower()
        else:
            # For placement, multiple_choice, fill_blank
            is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
        
        if is_correct:
            correct_count += 1
        
        question_results.append({
            'question_id': question_id,
            'question': question['question'],
            'user_answer': user_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct
        })
    
    score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
    
    results = {
        'score': correct_count,
        'total': total_questions,
        'percentage': round(score_percentage, 1),
        'question_results': question_results,
        'feedback': get_feedback_message(score_percentage)
    }
    
    return results

def get_feedback_message(percentage):
    """Get feedback message based on score"""
    if percentage >= 90:
        return "Outstanding! You know your music taste inside and out! 🎵"
    elif percentage >= 70:
        return "Great job! You're really in tune with your listening habits! 🎶"
    elif percentage >= 50:
        return "Not bad! You know your music, but there's always more to discover! 🎧"
    else:
        return "Keep exploring! Your music taste is always evolving! 🎼"

@app.route('/api/get-image/<item_type>/<item_id>')
def get_image(item_type, item_id):
    """Fetch image from Spotify API for tracks, albums, artists, or playlists"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        token_info = session['token_info']
        sp = spotipy.Spotify(auth=token_info['access_token'])
        
        image_url = None
        
        if item_type == 'track':
            track = sp.track(item_id)
            if track.get('album') and track['album'].get('images'):
                image_url = track['album']['images'][0]['url'] if track['album']['images'] else None
        elif item_type == 'album':
            album = sp.album(item_id)
            if album.get('images'):
                image_url = album['images'][0]['url'] if album['images'] else None
        elif item_type == 'artist':
            artist = sp.artist(item_id)
            if artist.get('images'):
                image_url = artist['images'][0]['url'] if artist['images'] else None
        elif item_type == 'playlist':
            playlist = sp.playlist(item_id)
            if playlist.get('images'):
                image_url = playlist['images'][0]['url'] if playlist['images'] else None
        
        return jsonify({'image_url': image_url})
    
    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return jsonify({'error': str(e), 'image_url': None}), 500

@app.route('/api/sync', methods=['POST'])
def sync_data():
    """Manually trigger data sync"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    try:
        token_info = session['token_info']
        sp = spotipy.Spotify(auth=token_info['access_token'])
        user = sp.current_user()
        
        sync_user_spotify_data(sp, user_id, user)
        session['data_synced'] = True
        
        return jsonify({'success': True, 'message': 'Data synced successfully'})
    
    except Exception as e:
        print(f"Error syncing data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)

