from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Album(db.Model):
    """User's saved albums"""
    __tablename__ = 'albums'
    
    id = db.Column(db.String(50), primary_key=True)  # Spotify album ID
    user_id = db.Column(db.String(50), db.ForeignKey('users.spotify_id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255))
    artist_id = db.Column(db.String(50))
    release_date = db.Column(db.String(50))
    total_tracks = db.Column(db.Integer)
    album_type = db.Column(db.String(50))
    external_url = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'artist': self.artist,
            'artist_id': self.artist_id,
            'release_date': self.release_date,
            'total_tracks': self.total_tracks,
            'album_type': self.album_type,
            'external_url': self.external_url,
            'image_url': self.image_url,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }

class SavedTrack(db.Model):
    """User's saved tracks"""
    __tablename__ = 'saved_tracks'
    
    id = db.Column(db.String(50), primary_key=True)  # Spotify track ID
    user_id = db.Column(db.String(50), db.ForeignKey('users.spotify_id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255))
    artist_id = db.Column(db.String(50))
    album_id = db.Column(db.String(50))
    album_name = db.Column(db.String(255))
    duration_ms = db.Column(db.Integer)
    popularity = db.Column(db.Integer)
    external_url = db.Column(db.String(255))
    preview_url = db.Column(db.String(255))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'artist': self.artist,
            'artist_id': self.artist_id,
            'album_id': self.album_id,
            'album_name': self.album_name,
            'duration_ms': self.duration_ms,
            'popularity': self.popularity,
            'external_url': self.external_url,
            'preview_url': self.preview_url,
            'added_at': self.added_at.isoformat() if self.added_at else None
        }

class Playlist(db.Model):
    """User's playlists"""
    __tablename__ = 'playlists'
    
    id = db.Column(db.String(50), primary_key=True)  # Spotify playlist ID
    user_id = db.Column(db.String(50), db.ForeignKey('users.spotify_id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    owner = db.Column(db.String(255))
    owner_id = db.Column(db.String(50))
    description = db.Column(db.Text)
    public = db.Column(db.Boolean, default=False)
    collaborative = db.Column(db.Boolean, default=False)
    total_tracks = db.Column(db.Integer)
    external_url = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'owner': self.owner,
            'owner_id': self.owner_id,
            'description': self.description,
            'public': self.public,
            'collaborative': self.collaborative,
            'total_tracks': self.total_tracks,
            'external_url': self.external_url,
            'image_url': self.image_url
        }

class TopTrack(db.Model):
    """User's top tracks"""
    __tablename__ = 'top_tracks'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    track_id = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.spotify_id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255))
    artist_id = db.Column(db.String(50))
    album_id = db.Column(db.String(50))
    album_name = db.Column(db.String(255))
    duration_ms = db.Column(db.Integer)
    popularity = db.Column(db.Integer)
    time_range = db.Column(db.String(20))  # short_term, medium_term, long_term
    rank = db.Column(db.Integer)  # Position in top tracks
    external_url = db.Column(db.String(255))
    preview_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'track_id': self.track_id,
            'name': self.name,
            'artist': self.artist,
            'artist_id': self.artist_id,
            'album_id': self.album_id,
            'album_name': self.album_name,
            'duration_ms': self.duration_ms,
            'popularity': self.popularity,
            'time_range': self.time_range,
            'rank': self.rank,
            'external_url': self.external_url,
            'preview_url': self.preview_url
        }

class TopArtist(db.Model):
    """User's top artists"""
    __tablename__ = 'top_artists'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artist_id = db.Column(db.String(50), nullable=False, index=True)
    user_id = db.Column(db.String(50), db.ForeignKey('users.spotify_id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    genres = db.Column(db.Text)  # JSON array of genres
    popularity = db.Column(db.Integer)
    followers = db.Column(db.Integer)
    time_range = db.Column(db.String(20))  # short_term, medium_term, long_term
    rank = db.Column(db.Integer)  # Position in top artists
    external_url = db.Column(db.String(255))
    image_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'artist_id': self.artist_id,
            'name': self.name,
            'genres': self.genres,
            'popularity': self.popularity,
            'followers': self.followers,
            'time_range': self.time_range,
            'rank': self.rank,
            'external_url': self.external_url,
            'image_url': self.image_url
        }

class User(db.Model):
    """User information"""
    __tablename__ = 'users'
    
    spotify_id = db.Column(db.String(50), primary_key=True)
    display_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    country = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_sync = db.Column(db.DateTime)
    
    # Relationships
    albums = db.relationship('Album', backref='user', lazy=True, cascade='all, delete-orphan')
    saved_tracks = db.relationship('SavedTrack', backref='user', lazy=True, cascade='all, delete-orphan')
    playlists = db.relationship('Playlist', backref='user', lazy=True, cascade='all, delete-orphan')
    top_tracks = db.relationship('TopTrack', backref='user', lazy=True, cascade='all, delete-orphan')
    top_artists = db.relationship('TopArtist', backref='user', lazy=True, cascade='all, delete-orphan')
