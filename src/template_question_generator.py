"""
Generate quiz questions from templates using user's listening history
"""
import json
import os
import random
from .models import Album, SavedTrack, Playlist, TopTrack, TopArtist


def load_templates():
    """Load question templates from JSON file"""
    template_path = os.path.join(os.path.dirname(__file__), 'question_templates.json')
    with open(template_path, 'r') as f:
        return json.load(f)


def get_user_data(user_id):
    """Get all user's listening data from database"""
    return {
        'albums': [album.to_dict() for album in Album.query.filter_by(user_id=user_id).all()],
        'saved_tracks': [track.to_dict() for track in SavedTrack.query.filter_by(user_id=user_id).all()],
        'playlists': [playlist.to_dict() for playlist in Playlist.query.filter_by(user_id=user_id).all()],
        'top_tracks': [track.to_dict() for track in TopTrack.query.filter_by(
            user_id=user_id, 
            time_range='medium_term'
        ).order_by(TopTrack.rank).all()],
        'top_artists': [artist.to_dict() for artist in TopArtist.query.filter_by(
            user_id=user_id,
            time_range='medium_term'
        ).order_by(TopArtist.rank).all()]
    }


def generate_placement_question(template, user_data):
    """Generate a placement question"""
    data_source = template['data_source']
    data = user_data.get(data_source, [])
    
    if not data or len(data) < template['rank_range'][1]:
        return None
    
    # Pick a random rank within range
    rank = random.randint(template['rank_range'][0], min(template['rank_range'][1], len(data)))
    
    # Get the item at that rank (assuming data is sorted by rank)
    correct_item = data[rank - 1]  # rank is 1-indexed, array is 0-indexed
    correct_answer = correct_item.get(template['field'])
    
    # Generate options: correct answer + 3 random wrong answers
    options = [correct_answer]
    wrong_options = [item.get(template['field']) for item in data 
                     if item.get(template['field']) and item.get(template['field']) != correct_answer]
    if len(wrong_options) >= 3:
        options.extend(random.sample(wrong_options, 3))
    elif len(wrong_options) > 0:
        options.extend(wrong_options)
    else:
        return None  # Not enough options
    
    random.shuffle(options)
    
    question_text = template['template'].format(rank=rank)
    
    # Add image URLs for options (if artists)
    image_urls = {}
    if data_source == 'top_artists':
        for option in options:
            artist = next((a for a in data if a.get('name') == option), None)
            if artist and artist.get('image_url'):
                image_urls[option] = artist.get('image_url')
    
    return {
        'type': 'placement',
        'question': question_text,
        'options': options,
        'correct_answer': correct_answer,
        'data': {
            'image_urls': image_urls
        }
    }


def generate_true_false_question(template, user_data):
    """Generate a true/false question"""
    data_source = template['data_source']
    data = user_data.get(data_source, [])
    
    if not data:
        return None
    
    # Randomly decide if answer should be true or false
    is_true = random.choice([True, False])
    
    if is_true:
        # Pick a random item that exists
        item = random.choice(data)
        correct_answer = 'true'
    else:
        # Generate a fake item name that doesn't exist
        item = {'name': f"Fake {random.choice(['Album', 'Track', 'Playlist'])} {random.randint(1000, 9999)}"}
        correct_answer = 'false'
    
    # Fill in template
    if 'album_name' in template['template']:
        question_text = template['template'].format(album_name=item.get('name', 'Unknown'))
    elif 'track_name' in template['template'] and 'artist_name' in template['template']:
        question_text = template['template'].format(
            track_name=item.get('name', 'Unknown'),
            artist_name=item.get('artist', 'Unknown Artist')
        )
    elif 'playlist_name' in template['template']:
        question_text = template['template'].format(playlist_name=item.get('name', 'Unknown'))
    elif 'artist_name' in template['template']:
        if template.get('check_type') == 'in_top_n':
            # Check if artist is in top N
            top_n = template.get('top_n', 10)
            top_artists = user_data.get('top_artists', [])[:top_n]
            artist_names = [a.get('name') for a in top_artists]
            if is_true:
                item = {'name': random.choice(artist_names) if artist_names else 'Unknown'}
            else:
                all_artists = user_data.get('top_artists', [])
                outside_top = [a for a in all_artists if a.get('name') not in artist_names]
                item = {'name': random.choice(outside_top).get('name') if outside_top else 'Unknown'}
        question_text = template['template'].format(artist_name=item.get('name', 'Unknown'))
    elif 'track_name' in template['template']:
        if template.get('check_type') == 'in_top_n':
            top_n = template.get('top_n', 10)
            top_tracks = user_data.get('top_tracks', [])[:top_n]
            track_names = [t.get('name') for t in top_tracks]
            if is_true:
                item = {'name': random.choice(track_names) if track_names else 'Unknown'}
            else:
                all_tracks = user_data.get('top_tracks', [])
                outside_top = [t for t in all_tracks if t.get('name') not in track_names]
                item = {'name': random.choice(outside_top).get('name') if outside_top else 'Unknown'}
        question_text = template['template'].format(track_name=item.get('name', 'Unknown'))
    else:
        question_text = template['template']
    
    return {
        'type': 'true_false',
        'question': question_text,
        'options': [],
        'correct_answer': correct_answer,
        'data': {}
    }


def generate_drag_drop_question(template, user_data):
    """Generate a drag and drop question"""
    data_source = template['data_source']
    data = user_data.get(data_source, [])
    count = template.get('count', 5)
    
    if not data or len(data) < count:
        return None
    
    # Get top N items sorted by rank
    items = data[:count]
    
    # Create items list with names and images
    question_items = []
    for item in items:
        item_data = {
            'name': item.get(template['field']),
            'image_url': item.get('image_url')  # Will be None for tracks, available for artists
        }
        # Add artist if available (for tracks)
        if 'artist' in item:
            item_data['artist'] = item.get('artist')
        # For tracks, store track_id so we can fetch image via API
        if data_source == 'top_tracks' and 'track_id' in item:
            item_data['track_id'] = item.get('track_id')
        question_items.append(item_data)
    
    # Correct order is the indices in order
    correct_order = list(range(len(question_items)))
    
    question_text = template['template']
    
    return {
        'type': 'drag_drop',
        'question': question_text,
        'options': [],
        'correct_answer': str(correct_order),  # Store as string, will parse later
        'data': {
            'items': question_items,
            'correct_order': correct_order
        }
    }


def generate_fill_blank_question(template, user_data):
    """Generate a fill in the blank question"""
    data_source = template['data_source']
    data = user_data.get(data_source, [])
    
    if not data:
        return None
    
    # Pick a random item
    item = random.choice(data)
    correct_answer = item.get(template['field'])
    
    question_text = template['template']
    
    # Get image URL if available
    image_url = item.get('image_url')
    
    return {
        'type': 'fill_blank',
        'question': question_text,
        'options': [],
        'correct_answer': correct_answer,
        'data': {
            'image_url': image_url,
            'playlist_name': correct_answer if data_source == 'playlists' else None
        }
    }


def generate_multiple_choice_question(template, user_data):
    """Generate a multiple choice question"""
    data_source = template['data_source']
    data = user_data.get(data_source, [])
    count = template.get('count', 4)
    
    if not data or len(data) < count:
        return None
    
    correct_answer = None
    
    if template.get('correct_answer') == 'rank_1':
        # Most played / #1 artist
        correct_item = data[0]  # First item (rank 1)
        correct_answer = correct_item.get(template['field'])
        if not correct_answer:
            return None
        # Get other random options
        other_items = random.sample(data[1:], min(count - 1, len(data) - 1))
        options = [correct_answer] + [item.get(template['field']) for item in other_items if item.get(template['field'])]
        if len(options) < count:
            return None
        
    elif template.get('correct_answer') == 'higher_rank':
        # Which is ranked higher
        selected = random.sample(data, min(count, len(data)))
        selected.sort(key=lambda x: x.get('rank', 999))
        correct_item = selected[0]  # Highest rank (lowest rank number)
        correct_answer = correct_item.get(template['field'])
        if not correct_answer:
            return None
        options = [item.get(template['field']) for item in selected if item.get(template['field'])]
        if len(options) < count:
            return None
    else:
        # Default: pick random items
        selected = random.sample(data, count)
        correct_item = selected[0]
        correct_answer = correct_item.get(template['field'])
        if not correct_answer:
            return None
        options = [item.get(template['field']) for item in selected if item.get(template['field'])]
        if len(options) < count:
            return None
    
    random.shuffle(options)
    
    question_text = template['template']
    
    return {
        'type': 'multiple_choice',
        'question': question_text,
        'options': options,
        'correct_answer': correct_answer,
        'data': {}
    }


def generate_questions(user_id, num_questions=10):
    """Generate questions from templates using user's data"""
    templates = load_templates()
    user_data = get_user_data(user_id)
    
    # Get all available question types
    question_types = list(templates.keys())
    
    # Randomize question types
    random.shuffle(question_types)
    
    questions = []
    type_counts = {qtype: 0 for qtype in question_types}
    
    # Generate questions, ensuring we get different types
    attempts = 0
    max_attempts = 50
    
    while len(questions) < num_questions and attempts < max_attempts:
        attempts += 1
        
        # Pick a question type (prioritize types we haven't used yet)
        unused_types = [t for t in question_types if type_counts[t] == 0]
        if unused_types:
            question_type = random.choice(unused_types)
        else:
            question_type = random.choice(question_types)
        
        # Get templates for this type
        type_templates = templates.get(question_type, [])
        if not type_templates:
            continue
        
        # Pick a random template
        template = random.choice(type_templates)
        
        # Generate question based on type
        question = None
        try:
            if question_type == 'placement':
                question = generate_placement_question(template, user_data)
            elif question_type == 'true_false':
                question = generate_true_false_question(template, user_data)
            elif question_type == 'drag_drop':
                question = generate_drag_drop_question(template, user_data)
            elif question_type == 'fill_blank':
                question = generate_fill_blank_question(template, user_data)
            elif question_type == 'multiple_choice':
                question = generate_multiple_choice_question(template, user_data)
        except Exception as e:
            print(f"Error generating {question_type} question: {e}")
            continue
        
        if question:
            question['id'] = f"q{len(questions) + 1}"
            questions.append(question)
            type_counts[question_type] += 1
    
    # If we didn't get enough questions, fill with random types
    while len(questions) < num_questions and attempts < max_attempts * 2:
        attempts += 1
        question_type = random.choice(question_types)
        type_templates = templates.get(question_type, [])
        if not type_templates:
            continue
        
        template = random.choice(type_templates)
        question = None
        
        try:
            if question_type == 'placement':
                question = generate_placement_question(template, user_data)
            elif question_type == 'true_false':
                question = generate_true_false_question(template, user_data)
            elif question_type == 'drag_drop':
                question = generate_drag_drop_question(template, user_data)
            elif question_type == 'fill_blank':
                question = generate_fill_blank_question(template, user_data)
            elif question_type == 'multiple_choice':
                question = generate_multiple_choice_question(template, user_data)
        except Exception as e:
            continue
        
        if question:
            question['id'] = f"q{len(questions) + 1}"
            questions.append(question)
    
    return questions
