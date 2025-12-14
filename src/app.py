import os
import secrets
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
from .models import db, User, Album, SavedTrack, Playlist, TopTrack, TopArtist, Lobby, LobbyParticipant
from .spotify_data import sync_user_spotify_data
from .template_question_generator import generate_questions
from .multiplayer_question_generator import generate_multiplayer_questions
import secrets
import string
import qrcode
import io
import base64
import json

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

def generate_lobby_code():
    """Generate a short, unique lobby code"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(characters) for _ in range(6))
        # Check if code already exists
        if not Lobby.query.filter_by(id=code).first():
            return code

def generate_qr_code(data):
    """Generate QR code image as base64 string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

@app.route('/')
def index():
    """Home page with quiz introduction"""
    return render_template('index.html')

@app.route('/lobby')
def lobby():
    """Lobby page for multiplayer game - host doesn't need Spotify"""
    lobby_id = session.get('lobby_id')
    if not lobby_id:
        # Create a new lobby (host doesn't need Spotify)
        lobby_code = generate_lobby_code()
        new_lobby = Lobby(
            id=lobby_code,
            host_user_id=None,  # Host doesn't need Spotify
            status='waiting'
        )
        db.session.add(new_lobby)
        db.session.commit()
        
        lobby_id = lobby_code
        session['lobby_id'] = lobby_id
    
    lobby_obj = Lobby.query.get(lobby_id)
    if not lobby_obj:
        session.pop('lobby_id', None)
        return redirect(url_for('lobby'))
    
    # Generate QR code for joining
    base_url = request.host_url.rstrip('/')
    join_url = f"{base_url}/join/{lobby_id}"
    qr_code = generate_qr_code(join_url)
    
    return render_template('lobby.html', lobby=lobby_obj, qr_code=qr_code, join_url=join_url)

@app.route('/join/<lobby_id>')
def join_lobby(lobby_id):
    """Join lobby page - for mobile users scanning QR code"""
    lobby_obj = Lobby.query.get(lobby_id)
    if not lobby_obj:
        return render_template('join_error.html', error="Lobby not found")
    
    if lobby_obj.status != 'waiting':
        return render_template('join_error.html', error="This lobby is no longer accepting players")
    
    # Check if user is already authenticated
    if 'token_info' in session and 'user_id' in session:
        user_id = session.get('user_id')
        # Check if already in lobby
        existing = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
        if existing:
            return render_template('join_lobby.html', lobby=lobby_obj, already_joined=True, game_name=existing.game_name)
        return render_template('join_lobby.html', lobby=lobby_obj, already_joined=False)
    
    # Not authenticated - redirect to login with return URL
    session['join_lobby_id'] = lobby_id
    return redirect(url_for('login'))

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
        
        # Check if user is joining a lobby
        join_lobby_id = session.get('join_lobby_id')
        if join_lobby_id:
            session.pop('join_lobby_id', None)
            return redirect(url_for('join_lobby', lobby_id=join_lobby_id))
        
        # Redirect to quiz page (single player)
        return redirect(url_for('quiz'))
    
    except Exception as e:
        # Log the error for debugging
        print(f"Callback error: {str(e)}")
        return f"An error occurred during authentication: {str(e)}", 500

@app.route('/quiz')
def quiz():
    """Main quiz page"""
    lobby_id = request.args.get('lobby')
    is_multiplayer = False
    lobby = None
    user_name = 'Player'
    is_mobile = request.args.get('mobile') == 'true' or request.user_agent.platform in ['iPhone', 'Android', 'Mobile']
    
    if lobby_id:
        # Multiplayer mode
        lobby = Lobby.query.get(lobby_id)
        if lobby and lobby.status == 'active':
            # Check if user is authenticated (participants need Spotify)
            if 'token_info' not in session:
                return redirect(url_for('join_lobby', lobby_id=lobby_id))
            
            user_id = session.get('user_id')
            participant = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
            if participant:
                is_multiplayer = True
                user_name = participant.game_name
            else:
                return redirect(url_for('join_lobby', lobby_id=lobby_id))
        elif lobby and lobby.status == 'waiting':
            return redirect(url_for('lobby'))
    else:
        # Single player mode - requires authentication
        if 'token_info' not in session:
            return redirect(url_for('login'))
        
        user_id = session.get('user_id')
        user_name = session.get('user_name', 'User')
        data_synced = session.get('data_synced', False)
    
    # Use mobile template for mobile devices in multiplayer
    if is_multiplayer and is_mobile:
        return render_template('quiz_mobile.html', 
                             user_name=user_name,
                             is_multiplayer=True,
                             lobby_id=lobby_id)
    
    return render_template('quiz.html', 
                         user_name=user_name, 
                         data_synced=session.get('data_synced', False) if not is_multiplayer else True,
                         is_multiplayer=is_multiplayer,
                         lobby_id=lobby_id)

@app.route('/api/quiz-questions', methods=['GET', 'POST'])
def get_quiz_questions():
    """Generate quiz questions from templates using user's listening data"""
    lobby_id = request.args.get('lobby') or (request.json.get('lobby_id') if request.is_json else None)
    
    if lobby_id:
        # Multiplayer mode
        lobby = Lobby.query.get(lobby_id)
        if not lobby or lobby.status != 'active':
            return jsonify({'error': 'Lobby not found or not active'}), 400
        
        # Check if questions already generated
        session_key = f'quiz_questions_{lobby_id}'
        if session_key not in session:
            # Generate questions using selected players' data
            selected_player_ids = []
            if lobby.selected_player_ids:
                try:
                    selected_player_ids = json.loads(lobby.selected_player_ids)
                except:
                    pass
            
            if not selected_player_ids:
                return jsonify({'error': 'No players selected for questions'}), 400
            
            # Get player names
            participants = LobbyParticipant.query.filter_by(lobby_id=lobby_id).all()
            player_names_map = {p.user_id: p.game_name for p in participants}
            
            # Generate multiplayer questions
            questions = generate_multiplayer_questions(
                lobby_id, 
                selected_player_ids, 
                player_names_map, 
                num_questions=10
            )
            
            if questions:
                session[session_key] = questions
            else:
                return jsonify({'error': 'Failed to generate questions'}), 500
        else:
            questions = session[session_key]
        
        return jsonify({
            'success': True,
            'questions': questions,
            'selected_players': [LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=pid).first().game_name 
                                for pid in json.loads(lobby.selected_player_ids) if lobby.selected_player_ids]
        })
    else:
        # Single player mode
        if 'token_info' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not found'}), 401
        
        # Generate questions from templates
        questions = generate_questions(user_id, num_questions=10)
        session['quiz_questions'] = questions
        
        if not questions or len(questions) == 0:
            return jsonify({'error': 'Not enough data to generate questions. Please make sure you have saved music, playlists, or top tracks/artists.'}), 400
        
        return jsonify({
            'success': True,
            'questions': questions
        })

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
    lobby_id = request.args.get('lobby')
    
    # Get results from appropriate session key
    if lobby_id:
        results = session.get(f'quiz_results_{lobby_id}')
        if not results:
            return redirect(url_for('quiz', lobby=lobby_id))
        
        # Get leaderboard for multiplayer
        lobby = Lobby.query.get(lobby_id)
        participants = LobbyParticipant.query.filter_by(lobby_id=lobby_id).order_by(LobbyParticipant.score.desc(), LobbyParticipant.completed_at.asc()).all()
        leaderboard = [p.to_dict() for p in participants]
        
        return render_template('results.html', results=results, is_multiplayer=True, lobby_id=lobby_id, leaderboard=leaderboard)
    else:
        results = session.get('quiz_results')
        if not results:
            return redirect(url_for('quiz'))
        
        return render_template('results.html', results=results, is_multiplayer=False)

@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    """Process quiz answers and calculate results"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    data = request.json
    answers = data.get('answers', {})
    lobby_id = data.get('lobby_id')
    
    # Get questions from appropriate session key
    if lobby_id:
        questions = session.get(f'quiz_questions_{lobby_id}', [])
    else:
        questions = session.get('quiz_questions', [])
    
    if not questions:
        return jsonify({'error': 'No questions found'}), 400
    
    try:
        # Calculate results based on answers
        results = calculate_quiz_results(answers, questions)
        
        # If multiplayer, update participant score
        if lobby_id:
            participant = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
            if participant:
                from datetime import datetime
                participant.score = results['score']
                participant.completed_at = datetime.utcnow()
                db.session.commit()
        
        # Store results in session
        if lobby_id:
            session[f'quiz_results_{lobby_id}'] = results
        else:
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

@app.route('/api/lobby/<lobby_id>/status')
def lobby_status(lobby_id):
    """Get lobby status and participants"""
    lobby = Lobby.query.get(lobby_id)
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    participants = [p.to_dict() for p in lobby.participants]
    
    return jsonify({
        'lobby': lobby.to_dict(),
        'participants': participants
    })

@app.route('/api/lobby/<lobby_id>/join', methods=['POST'])
def api_join_lobby(lobby_id):
    """API endpoint to join a lobby"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    lobby = Lobby.query.get(lobby_id)
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    if lobby.status != 'waiting':
        return jsonify({'error': 'Lobby is no longer accepting players'}), 400
    
    # Get game name from request
    data = request.json
    game_name = data.get('game_name', '').strip()
    if not game_name:
        return jsonify({'error': 'Game name is required'}), 400
    
    # Check if already in lobby
    existing = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
    if existing:
        existing.game_name = game_name
        db.session.commit()
        return jsonify({'success': True, 'message': 'Updated game name', 'participant': existing.to_dict()})
    
    # Add participant
    participant = LobbyParticipant(
        lobby_id=lobby_id,
        user_id=user_id,
        game_name=game_name
    )
    db.session.add(participant)
    db.session.commit()
    
    return jsonify({'success': True, 'participant': participant.to_dict()})

@app.route('/api/lobby/<lobby_id>/start', methods=['POST'])
def start_lobby_game(lobby_id):
    """Start the game for a lobby"""
    # Host doesn't need to be authenticated with Spotify
    lobby = Lobby.query.get(lobby_id)
    
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    if lobby.status != 'waiting':
        return jsonify({'error': 'Game has already started'}), 400
    
    participants = lobby.participants
    if len(participants) < 1:
        return jsonify({'error': 'Need at least one participant to start'}), 400
    
    # Select up to 4 players randomly (or all if less than 4)
    selected_participants = random.sample(participants, min(4, len(participants)))
    selected_player_ids = [p.user_id for p in selected_participants]
    
    # Store selected players in lobby
    lobby.selected_player_ids = json.dumps(selected_player_ids)
    
    # Start the game
    from datetime import datetime
    lobby.status = 'active'
    lobby.started_at = datetime.utcnow()
    lobby.current_question = 0
    db.session.commit()
    
    # Get player names for announcement
    selected_names = [p.game_name for p in selected_participants]
    
    return jsonify({
        'success': True, 
        'lobby': lobby.to_dict(),
        'selected_players': selected_names
    })

@app.route('/api/lobby/<lobby_id>/leave', methods=['POST'])
def leave_lobby(lobby_id):
    """Leave a lobby"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    participant = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
    
    if participant:
        db.session.delete(participant)
        db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/lobby/<lobby_id>/submit-answer', methods=['POST'])
def submit_question_answer(lobby_id):
    """Submit answer for a single question in multiplayer"""
    if 'token_info' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_id = session.get('user_id')
    participant = LobbyParticipant.query.filter_by(lobby_id=lobby_id, user_id=user_id).first()
    
    if not participant:
        return jsonify({'error': 'Not a participant in this lobby'}), 403
    
    data = request.json
    question_id = data.get('question_id')
    answer = data.get('answer')
    question_index = data.get('question_index', 0)
    
    if not question_id or answer is None:
        return jsonify({'error': 'Missing question_id or answer'}), 400
    
    # Update participant's answers
    answers_dict = {}
    if participant.answers:
        try:
            answers_dict = json.loads(participant.answers)
        except:
            pass
    
    answers_dict[question_id] = answer
    participant.answers = json.dumps(answers_dict)
    participant.current_question = question_index
    participant.question_submitted = question_index
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/lobby/<lobby_id>/question-status')
def get_question_status(lobby_id):
    """Get status of current question - who has answered"""
    lobby = Lobby.query.get(lobby_id)
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    participants = LobbyParticipant.query.filter_by(lobby_id=lobby_id).all()
    current_question = lobby.current_question
    
    status = {
        'current_question': current_question,
        'total_participants': len(participants),
        'answered': 0,
        'participants': []
    }
    
    for p in participants:
        p_dict = p.to_dict()
        has_answered = p.question_submitted >= current_question
        p_dict['has_answered'] = has_answered
        status['participants'].append(p_dict)
        if has_answered:
            status['answered'] += 1
    
    return jsonify(status)

@app.route('/api/lobby/<lobby_id>/leaderboard')
def get_leaderboard(lobby_id):
    """Get current leaderboard"""
    participants = LobbyParticipant.query.filter_by(lobby_id=lobby_id).order_by(
        LobbyParticipant.score.desc(), 
        LobbyParticipant.completed_at.asc()
    ).all()
    
    leaderboard = [p.to_dict() for p in participants]
    return jsonify({'leaderboard': leaderboard})

@app.route('/api/lobby/<lobby_id>/next-question', methods=['POST'])
def next_question(lobby_id):
    """Move to next question (host only)"""
    lobby = Lobby.query.get(lobby_id)
    if not lobby:
        return jsonify({'error': 'Lobby not found'}), 404
    
    lobby.current_question += 1
    db.session.commit()
    
    return jsonify({'success': True, 'current_question': lobby.current_question})

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)

