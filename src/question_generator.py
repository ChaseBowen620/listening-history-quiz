"""
Generate quiz questions using OpenAI ChatGPT based on user's listening history
"""
import os
import json
from openai import OpenAI
from .models import Album, SavedTrack, Playlist, TopTrack, TopArtist


def get_user_listening_summary(user_id):
    """Get a summary of user's listening history for the prompt"""
    summary = {
        'albums_count': Album.query.filter_by(user_id=user_id).count(),
        'saved_tracks_count': SavedTrack.query.filter_by(user_id=user_id).count(),
        'playlists_count': Playlist.query.filter_by(user_id=user_id).count(),
        'top_tracks': [],
        'top_artists': [],
        'sample_albums': [],
        'sample_tracks': [],
        'sample_playlists': []
    }
    
    # Get top tracks (medium_term)
    top_tracks = TopTrack.query.filter_by(
        user_id=user_id, 
        time_range='medium_term'
    ).order_by(TopTrack.rank).limit(20).all()
    
    summary['top_tracks'] = [
        {
            'rank': track.rank,
            'name': track.name,
            'artist': track.artist,
            'album': track.album_name
        }
        for track in top_tracks
    ]
    
    # Get top artists (medium_term)
    top_artists = TopArtist.query.filter_by(
        user_id=user_id,
        time_range='medium_term'
    ).order_by(TopArtist.rank).limit(20).all()
    
    summary['top_artists'] = [
        {
            'rank': artist.rank,
            'name': artist.name,
            'genres': json.loads(artist.genres) if artist.genres else []
        }
        for artist in top_artists
    ]
    
    # Get sample albums
    albums = Album.query.filter_by(user_id=user_id).limit(15).all()
    summary['sample_albums'] = [
        {
            'name': album.name,
            'artist': album.artist,
            'release_date': album.release_date
        }
        for album in albums
    ]
    
    # Get sample saved tracks
    tracks = SavedTrack.query.filter_by(user_id=user_id).limit(15).all()
    summary['sample_tracks'] = [
        {
            'name': track.name,
            'artist': track.artist,
            'album': track.album_name
        }
        for track in tracks
    ]
    
    # Get sample playlists
    playlists = Playlist.query.filter_by(user_id=user_id).limit(10).all()
    summary['sample_playlists'] = [
        {
            'name': playlist.name,
            'total_tracks': playlist.total_tracks,
            'description': playlist.description
        }
        for playlist in playlists
    ]
    
    return summary


def generate_questions(user_id):
    """Generate 5 quiz questions using OpenAI ChatGPT"""
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables")
    
    client = OpenAI(api_key=openai_api_key)
    
    # Get user's listening history summary
    listening_data = get_user_listening_summary(user_id)
    
    # Create prompt for ChatGPT
    prompt = f"""You are creating a fun, personalized music quiz based on a user's Spotify listening history. 
Generate exactly 5 diverse questions about their music taste and listening habits.

The user's listening data:
- They have {listening_data['albums_count']} saved albums
- They have {listening_data['saved_tracks_count']} saved tracks
- They have {listening_data['playlists_count']} playlists

Top Tracks (ranked):
{json.dumps(listening_data['top_tracks'], indent=2)}

Top Artists (ranked):
{json.dumps(listening_data['top_artists'], indent=2)}

Sample Albums:
{json.dumps(listening_data['sample_albums'], indent=2)}

Sample Saved Tracks:
{json.dumps(listening_data['sample_tracks'], indent=2)}

Sample Playlists:
{json.dumps(listening_data['sample_playlists'], indent=2)}

Create 5 questions with these requirements:
1. Use different question types: placement (e.g., "Who is your 5th favorite artist?"), true/false, drag-and-drop ordering, fill-in-the-blank, multiple choice
2. Questions should be specific to their actual listening data (use real artist names, track names, ranks, etc.)
3. Make questions fun and engaging
4. Include the correct answer for each question
5. For placement questions, use ranks from 1-20
6. For true/false, use actual facts from their data
7. For drag-and-drop, ask them to order tracks/artists by their rank
8. For fill-in-the-blank, use playlist names, artist names, or track names

Return ONLY a valid JSON array with this exact structure:

For placement questions:
{{
  "id": "q1",
  "type": "placement",
  "question": "Who is your 5th favorite artist?",
  "options": ["Artist Name 1", "Artist Name 2", "Artist Name 3", "Artist Name 4"],
  "correct_answer": "Artist Name 1",
  "data": {{}}
}}

For true/false questions:
{{
  "id": "q2",
  "type": "true_false",
  "question": "You have saved the album 'Album Name' in your library.",
  "options": [],
  "correct_answer": "true",
  "data": {{}}
}}

For drag-and-drop questions:
{{
  "id": "q3",
  "type": "drag_drop",
  "question": "Order these tracks by their rank in your top tracks (1st to 5th):",
  "options": [],
  "correct_answer": "[0,1,2,3,4]",
  "data": {{
    "items": [
      {{"name": "Track Name 1", "artist": "Artist Name"}},
      {{"name": "Track Name 2", "artist": "Artist Name"}},
      {{"name": "Track Name 3", "artist": "Artist Name"}},
      {{"name": "Track Name 4", "artist": "Artist Name"}},
      {{"name": "Track Name 5", "artist": "Artist Name"}}
    ]
  }}
}}

For fill-in-the-blank questions:
{{
  "id": "q4",
  "type": "fill_blank",
  "question": "What is the name of this playlist?",
  "options": [],
  "correct_answer": "Playlist Name",
  "data": {{
    "playlist_name": "Playlist Name"
  }}
}}

For multiple choice questions:
{{
  "id": "q5",
  "type": "multiple_choice",
  "question": "Which of these is your most played track?",
  "options": ["Track Name 1", "Track Name 2", "Track Name 3", "Track Name 4"],
  "correct_answer": "Track Name 1",
  "data": {{}}
}}

IMPORTANT:
- Use actual data from the user's listening history provided above
- For drag_drop, use exactly 5 items from their top tracks or top artists
- For placement, use ranks between 1-20 from their actual data
- For fill_blank, use actual playlist names from their data
- Make sure all JSON is valid and parseable
- Do not include any text before or after the JSON array"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency, can upgrade to gpt-4 if needed
            messages=[
                {"role": "system", "content": "You are a helpful assistant that creates music quiz questions. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # Extract and parse JSON from response
        content = response.choices[0].message.content.strip()
        
        # Try to extract JSON if there's extra text
        if content.startswith('```json'):
            content = content[7:]
        if content.startswith('```'):
            content = content[3:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        questions = json.loads(content)
        
        # Validate we got 5 questions
        if not isinstance(questions, list) or len(questions) != 5:
            raise ValueError(f"Expected 5 questions, got {len(questions) if isinstance(questions, list) else 'invalid format'}")
        
        # Add image URLs and enrich data
        enriched_questions = []
        for q in questions:
            enriched_q = enrich_question_with_images(q, user_id)
            enriched_questions.append(enriched_q)
        
        return enriched_questions
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response content: {content[:500]}")
        raise ValueError(f"Failed to parse questions JSON: {str(e)}")
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise


def enrich_question_with_images(question, user_id):
    """Add image URLs and additional data to questions"""
    question_type = question.get('type')
    
    # Ensure data object exists
    if 'data' not in question:
        question['data'] = {}
    
    # Add image URLs based on question type
    if question_type == 'drag_drop':
        # For drag-drop, get track/artist images
        items = question['data'].get('items', [])
        
        enriched_items = []
        for item in items:
            item_name = item.get('name') or str(item)
            enriched_item = {'name': item_name}
            
            # Try to find track in database
            track = TopTrack.query.filter_by(
                user_id=user_id
            ).filter(
                TopTrack.name.ilike(f'%{item_name}%')
            ).first()
            
            if track:
                enriched_item['image_url'] = track.external_url  # We'll need to fetch image via API
                enriched_item['artist'] = track.artist
            else:
                # Try to find artist
                artist = TopArtist.query.filter_by(
                    user_id=user_id
                ).filter(
                    TopArtist.name.ilike(f'%{item_name}%')
                ).first()
                
                if artist:
                    enriched_item['image_url'] = artist.image_url
                    enriched_item['artist'] = None
            
            enriched_items.append(enriched_item)
        
        question['data']['items'] = enriched_items
        # Store correct order for validation
        question['data']['correct_order'] = list(range(len(enriched_items)))
    
    elif question_type == 'fill_blank':
        # For fill-in-blank with playlists, add playlist image
        playlist_name = question.get('data', {}).get('playlist_name')
        if playlist_name:
            playlist = Playlist.query.filter_by(
                user_id=user_id,
                name=playlist_name
            ).first()
            if playlist:
                question['data']['image_url'] = playlist.image_url
    
    elif 'placement' in question_type or 'multiple_choice' in question_type:
        # For placement/multiple choice about artists, add artist images
        if 'artist' in question.get('question', '').lower() or 'artist' in str(question.get('options', [])).lower():
            if 'image_urls' not in question['data']:
                question['data']['image_urls'] = {}
            
            for option in question.get('options', []):
                # Try exact match first
                artist = TopArtist.query.filter_by(
                    user_id=user_id,
                    name=option
                ).first()
                
                # If not found, try partial match
                if not artist:
                    artist = TopArtist.query.filter_by(
                        user_id=user_id
                    ).filter(
                        TopArtist.name.ilike(f'%{option}%')
                    ).first()
                
                if artist and artist.image_url:
                    question['data']['image_urls'][option] = artist.image_url
    
    return question
