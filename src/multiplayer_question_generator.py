"""
Generate multiplayer questions using data from selected players
"""
import json
import random
from .models import Album, SavedTrack, Playlist, TopTrack, TopArtist, LobbyParticipant


def get_time_range_label(time_range):
    """Get human-readable time range label"""
    labels = {
        'short_term': 'last month',
        'medium_term': 'last 6 months',
        'long_term': 'last year'
    }
    return labels.get(time_range, time_range)


def get_player_data(user_id, time_range=None):
    """Get all data for a specific player"""
    data = {
        'albums': [album.to_dict() for album in Album.query.filter_by(user_id=user_id).all()],
        'saved_tracks': [track.to_dict() for track in SavedTrack.query.filter_by(user_id=user_id).all()],
        'playlists': [playlist.to_dict() for playlist in Playlist.query.filter_by(user_id=user_id).all()],
        'top_tracks': [],
        'top_artists': []
    }
    
    # Get top tracks and artists for all time ranges or specific one
    if time_range:
        time_ranges = [time_range]
    else:
        time_ranges = ['short_term', 'medium_term', 'long_term']
    
    for tr in time_ranges:
        tracks = TopTrack.query.filter_by(user_id=user_id, time_range=tr).order_by(TopTrack.rank).all()
        data['top_tracks'].extend([t.to_dict() for t in tracks])
        
        artists = TopArtist.query.filter_by(user_id=user_id, time_range=tr).order_by(TopArtist.rank).all()
        data['top_artists'].extend([a.to_dict() for a in artists])
    
    return data


def generate_multiplayer_questions(lobby_id, selected_player_ids, player_names_map, num_questions=10):
    """Generate questions using data from selected players"""
    questions = []
    
    # Get data for all selected players
    players_data = {}
    for user_id in selected_player_ids:
        players_data[user_id] = get_player_data(user_id)
    
    # Time ranges to use
    time_ranges = ['short_term', 'medium_term', 'long_term']
    time_range_labels = {
        'short_term': 'last month',
        'medium_term': 'last 6 months',
        'long_term': 'last year'
    }
    
    question_types = ['placement', 'true_false', 'multiple_choice', 'drag_drop', 'fill_blank']
    
    attempts = 0
    max_attempts = 100
    
    while len(questions) < num_questions and attempts < max_attempts:
        attempts += 1
        
        # Pick a random player
        player_id = random.choice(selected_player_ids)
        player_name = player_names_map.get(player_id, 'Player')
        player_data = players_data[player_id]
        
        # Pick a random time range
        time_range = random.choice(time_ranges)
        time_label = time_range_labels[time_range]
        
        # Get data for this time range
        player_tracks = [t for t in player_data['top_tracks'] if t.get('time_range') == time_range]
        player_artists = [a for a in player_data['top_artists'] if a.get('time_range') == time_range]
        
        question_type = random.choice(question_types)
        question = None
        
        try:
            if question_type == 'placement' and len(player_artists) >= 5:
                # "What was Player A's 3rd favorite artist (last 6 months)?"
                rank = random.randint(1, min(20, len(player_artists)))
                correct_artist = player_artists[rank - 1]
                correct_answer = correct_artist.get('name')
                
                # Generate options
                options = [correct_answer]
                other_artists = [a.get('name') for a in player_artists if a.get('name') != correct_answer]
                options.extend(random.sample(other_artists, min(3, len(other_artists))))
                random.shuffle(options)
                
                question = {
                    'type': 'placement',
                    'question': f"What was {player_name}'s {rank}{'st' if rank == 1 else 'nd' if rank == 2 else 'rd' if rank == 3 else 'th'} favorite artist ({time_label})?",
                    'options': options,
                    'correct_answer': correct_answer,
                    'data': {
                        'player_name': player_name,
                        'time_range': time_range,
                        'time_label': time_label
                    }
                }
                
            elif question_type == 'true_false':
                # "Does Player A have the album 'X' saved?"
                if len(player_data['albums']) > 0:
                    is_true = random.choice([True, False])
                    if is_true:
                        album = random.choice(player_data['albums'])
                        correct_answer = 'true'
                    else:
                        album = {'name': f"Fake Album {random.randint(1000, 9999)}"}
                        correct_answer = 'false'
                    
                    question = {
                        'type': 'true_false',
                        'question': f"Does {player_name} have the album '{album.get('name')}' saved?",
                        'options': [],
                        'correct_answer': correct_answer,
                        'data': {
                            'player_name': player_name
                        }
                    }
                
            elif question_type == 'multiple_choice' and len(player_tracks) >= 4:
                # "Who had [track] as their 5th favorite track (last month)?"
                # Pick a random track from one player
                source_player_id = random.choice(selected_player_ids)
                source_player_name = player_names_map.get(source_player_id, 'Player')
                source_data = players_data[source_player_id]
                source_tracks = [t for t in source_data['top_tracks'] if t.get('time_range') == time_range]
                
                if len(source_tracks) >= 5:
                    track = source_tracks[4]  # 5th track (0-indexed)
                    track_name = track.get('name')
                    
                    # Find which players have this track
                    players_with_track = []
                    for pid in selected_player_ids:
                        pdata = players_data[pid]
                        ptracks = [t for t in pdata['top_tracks'] if t.get('time_range') == time_range]
                        for t in ptracks:
                            if t.get('name') == track_name:
                                players_with_track.append(pid)
                                break
                    
                    if len(players_with_track) > 0:
                        correct_player_id = random.choice(players_with_track)
                        correct_answer = player_names_map.get(correct_player_id, 'Player')
                        
                        # Generate options
                        options = [correct_answer]
                        other_players = [player_names_map.get(pid, 'Player') for pid in selected_player_ids if pid != correct_player_id]
                        options.extend(random.sample(other_players, min(3, len(other_players))))
                        random.shuffle(options)
                        
                        question = {
                            'type': 'multiple_choice',
                            'question': f"Who had '{track_name}' as their 5th favorite track ({time_label})?",
                            'options': options,
                            'correct_answer': correct_answer,
                            'data': {
                                'time_range': time_range,
                                'time_label': time_label
                            }
                        }
            
            elif question_type == 'drag_drop' and len(player_tracks) >= 5:
                # "Order these tracks by Player A's ranking (last 6 months):"
                tracks = player_tracks[:5]
                question_items = [{'name': t.get('name'), 'artist': t.get('artist')} for t in tracks]
                correct_order = list(range(len(question_items)))
                
                question = {
                    'type': 'drag_drop',
                    'question': f"Order these tracks by {player_name}'s ranking ({time_label}):",
                    'options': [],
                    'correct_answer': str(correct_order),
                    'data': {
                        'items': question_items,
                        'correct_order': correct_order,
                        'player_name': player_name,
                        'time_range': time_range,
                        'time_label': time_label
                    }
                }
                
            elif question_type == 'fill_blank' and len(player_data['playlists']) > 0:
                # "What is the name of this playlist from Player A?"
                playlist = random.choice(player_data['playlists'])
                correct_answer = playlist.get('name')
                image_url = playlist.get('image_url')
                
                question = {
                    'type': 'fill_blank',
                    'question': f"What is the name of this playlist from {player_name}?",
                    'options': [],
                    'correct_answer': correct_answer,
                    'data': {
                        'image_url': image_url,
                        'player_name': player_name
                    }
                }
        
        except Exception as e:
            print(f"Error generating {question_type} question: {e}")
            continue
        
        if question:
            question['id'] = f"q{len(questions) + 1}"
            questions.append(question)
    
    return questions
