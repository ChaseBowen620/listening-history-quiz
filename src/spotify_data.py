"""
Functions to fetch and process Spotify data
"""
import json
from datetime import datetime
from spotipy import Spotify
from .models import db, Album, SavedTrack, Playlist, TopTrack, TopArtist, User


def parse_spotify_date(date_str):
    """Parse Spotify date string to datetime object"""
    if not date_str:
        return None
    try:
        # Try ISO format first
        if 'T' in date_str:
            date_str = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(date_str)
    except:
        try:
            # Try parsing as regular datetime
            return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
        except:
            return None


def fetch_user_saved_albums(sp: Spotify, limit=50):
    """Fetch user's saved albums from Spotify"""
    albums = []
    results = sp.current_user_saved_albums(limit=limit)
    
    while results:
        albums.extend(results['items'])
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return albums


def fetch_user_saved_tracks(sp: Spotify, limit=50):
    """Fetch user's saved tracks from Spotify"""
    tracks = []
    results = sp.current_user_saved_tracks(limit=limit)
    
    while results:
        tracks.extend(results['items'])
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return tracks


def fetch_user_playlists(sp: Spotify, limit=50):
    """Fetch user's playlists from Spotify"""
    playlists = []
    results = sp.current_user_playlists(limit=limit)
    
    while results:
        playlists.extend(results['items'])
        if results['next']:
            results = sp.next(results)
        else:
            break
    
    return playlists


def fetch_user_top_tracks(sp: Spotify, time_range='medium_term', limit=50):
    """Fetch user's top tracks from Spotify"""
    results = sp.current_user_top_tracks(time_range=time_range, limit=limit)
    return results['items']


def fetch_user_top_artists(sp: Spotify, time_range='medium_term', limit=50):
    """Fetch user's top artists from Spotify"""
    results = sp.current_user_top_artists(time_range=time_range, limit=limit)
    return results['items']


def process_and_store_albums(albums_data, user_id):
    """Process albums JSON and store in database"""
    # Delete existing albums for this user
    Album.query.filter_by(user_id=user_id).delete()
    
    albums = []
    for item in albums_data:
        album_data = item['album']
        # Parse added_at date - handle different formats
        added_at = None
        if item.get('added_at'):
            try:
                added_at = date_parser.parse(item['added_at'])
            except:
                try:
                    added_at = datetime.fromisoformat(item['added_at'].replace('Z', '+00:00'))
                except:
                    pass
        
        # Get primary artist
        artist_name = album_data['artists'][0]['name'] if album_data['artists'] else None
        artist_id = album_data['artists'][0]['id'] if album_data['artists'] else None
        
        # Get image URL
        image_url = None
        if album_data.get('images'):
            image_url = album_data['images'][0]['url'] if album_data['images'] else None
        
        album = Album(
            id=album_data['id'],
            user_id=user_id,
            name=album_data['name'],
            artist=artist_name,
            artist_id=artist_id,
            release_date=album_data.get('release_date'),
            total_tracks=album_data.get('total_tracks'),
            album_type=album_data.get('album_type'),
            external_url=album_data['external_urls'].get('spotify') if album_data.get('external_urls') else None,
            image_url=image_url,
            added_at=added_at
        )
        albums.append(album)
    
    db.session.bulk_save_objects(albums)
    db.session.commit()
    return len(albums)


def process_and_store_saved_tracks(tracks_data, user_id):
    """Process saved tracks JSON and store in database"""
    # Delete existing saved tracks for this user
    SavedTrack.query.filter_by(user_id=user_id).delete()
    
    tracks = []
    for item in tracks_data:
        track_data = item['track']
        added_at = parse_spotify_date(item.get('added_at'))
        
        # Get primary artist
        artist_name = track_data['artists'][0]['name'] if track_data['artists'] else None
        artist_id = track_data['artists'][0]['id'] if track_data['artists'] else None
        
        # Get album info
        album_id = track_data['album']['id'] if track_data.get('album') else None
        album_name = track_data['album']['name'] if track_data.get('album') else None
        
        track = SavedTrack(
            id=track_data['id'],
            user_id=user_id,
            name=track_data['name'],
            artist=artist_name,
            artist_id=artist_id,
            album_id=album_id,
            album_name=album_name,
            duration_ms=track_data.get('duration_ms'),
            popularity=track_data.get('popularity'),
            external_url=track_data['external_urls'].get('spotify') if track_data.get('external_urls') else None,
            preview_url=track_data.get('preview_url'),
            added_at=added_at
        )
        tracks.append(track)
    
    db.session.bulk_save_objects(tracks)
    db.session.commit()
    return len(tracks)


def process_and_store_playlists(playlists_data, user_id):
    """Process playlists JSON and store in database"""
    # Delete existing playlists for this user
    Playlist.query.filter_by(user_id=user_id).delete()
    
    playlists = []
    for playlist_data in playlists_data:
        # Get image URL
        image_url = None
        if playlist_data.get('images'):
            image_url = playlist_data['images'][0]['url'] if playlist_data['images'] else None
        
        playlist = Playlist(
            id=playlist_data['id'],
            user_id=user_id,
            name=playlist_data['name'],
            owner=playlist_data['owner'].get('display_name') if playlist_data.get('owner') else None,
            owner_id=playlist_data['owner'].get('id') if playlist_data.get('owner') else None,
            description=playlist_data.get('description'),
            public=playlist_data.get('public', False),
            collaborative=playlist_data.get('collaborative', False),
            total_tracks=playlist_data['tracks'].get('total') if playlist_data.get('tracks') else 0,
            external_url=playlist_data['external_urls'].get('spotify') if playlist_data.get('external_urls') else None,
            image_url=image_url
        )
        playlists.append(playlist)
    
    db.session.bulk_save_objects(playlists)
    db.session.commit()
    return len(playlists)


def process_and_store_top_tracks(tracks_data, user_id, time_range='medium_term'):
    """Process top tracks JSON and store in database"""
    # Delete existing top tracks for this user and time range
    TopTrack.query.filter_by(user_id=user_id, time_range=time_range).delete()
    
    tracks = []
    for rank, track_data in enumerate(tracks_data, start=1):
        # Get primary artist
        artist_name = track_data['artists'][0]['name'] if track_data['artists'] else None
        artist_id = track_data['artists'][0]['id'] if track_data['artists'] else None
        
        # Get album info
        album_id = track_data['album']['id'] if track_data.get('album') else None
        album_name = track_data['album']['name'] if track_data.get('album') else None
        
        track = TopTrack(
            track_id=track_data['id'],
            user_id=user_id,
            name=track_data['name'],
            artist=artist_name,
            artist_id=artist_id,
            album_id=album_id,
            album_name=album_name,
            duration_ms=track_data.get('duration_ms'),
            popularity=track_data.get('popularity'),
            time_range=time_range,
            rank=rank,
            external_url=track_data['external_urls'].get('spotify') if track_data.get('external_urls') else None,
            preview_url=track_data.get('preview_url')
        )
        tracks.append(track)
    
    db.session.bulk_save_objects(tracks)
    db.session.commit()
    return len(tracks)


def process_and_store_top_artists(artists_data, user_id, time_range='medium_term'):
    """Process top artists JSON and store in database"""
    # Delete existing top artists for this user and time range
    TopArtist.query.filter_by(user_id=user_id, time_range=time_range).delete()
    
    artists = []
    for rank, artist_data in enumerate(artists_data, start=1):
        # Get image URL
        image_url = None
        if artist_data.get('images'):
            image_url = artist_data['images'][0]['url'] if artist_data['images'] else None
        
        # Store genres as JSON string
        genres_json = json.dumps(artist_data.get('genres', []))
        
        artist = TopArtist(
            artist_id=artist_data['id'],
            user_id=user_id,
            name=artist_data['name'],
            genres=genres_json,
            popularity=artist_data.get('popularity'),
            followers=artist_data.get('followers', {}).get('total') if artist_data.get('followers') else None,
            time_range=time_range,
            rank=rank,
            external_url=artist_data['external_urls'].get('spotify') if artist_data.get('external_urls') else None,
            image_url=image_url
        )
        artists.append(artist)
    
    db.session.bulk_save_objects(artists)
    db.session.commit()
    return len(artists)


def sync_user_spotify_data(sp: Spotify, user_id: str, user_info: dict):
    """Main function to fetch and store all user Spotify data"""
    try:
        # Create or update user record
        user = User.query.get(user_id)
        if not user:
            user = User(
                spotify_id=user_id,
                display_name=user_info.get('display_name'),
                email=user_info.get('email'),
                country=user_info.get('country')
            )
            db.session.add(user)
        else:
            user.display_name = user_info.get('display_name')
            user.email = user_info.get('email')
            user.country = user_info.get('country')
        
        user.last_sync = datetime.utcnow()
        db.session.commit()
        
        # Fetch and store all data
        print(f"Fetching Spotify data for user {user_id}...")
        
        # Saved albums
        print("Fetching saved albums...")
        albums_data = fetch_user_saved_albums(sp, limit=50)
        albums_count = process_and_store_albums(albums_data, user_id)
        print(f"Stored {albums_count} albums")
        
        # Saved tracks
        print("Fetching saved tracks...")
        tracks_data = fetch_user_saved_tracks(sp, limit=50)
        tracks_count = process_and_store_saved_tracks(tracks_data, user_id)
        print(f"Stored {tracks_count} saved tracks")
        
        # Playlists
        print("Fetching playlists...")
        playlists_data = fetch_user_playlists(sp, limit=50)
        playlists_count = process_and_store_playlists(playlists_data, user_id)
        print(f"Stored {playlists_count} playlists")
        
        # Top tracks (for all time ranges)
        for time_range in ['short_term', 'medium_term', 'long_term']:
            print(f"Fetching top tracks ({time_range})...")
            top_tracks_data = fetch_user_top_tracks(sp, time_range=time_range, limit=50)
            top_tracks_count = process_and_store_top_tracks(top_tracks_data, user_id, time_range=time_range)
            print(f"Stored {top_tracks_count} top tracks for {time_range}")
        
        # Top artists (for all time ranges)
        for time_range in ['short_term', 'medium_term', 'long_term']:
            print(f"Fetching top artists ({time_range})...")
            top_artists_data = fetch_user_top_artists(sp, time_range=time_range, limit=50)
            top_artists_count = process_and_store_top_artists(top_artists_data, user_id, time_range=time_range)
            print(f"Stored {top_artists_count} top artists for {time_range}")
        
        print(f"Successfully synced all Spotify data for user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error syncing Spotify data: {str(e)}")
        db.session.rollback()
        raise
