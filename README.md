# Spotify Quiz App 🎵

A fun and interactive web application that analyzes your Spotify listening habits and creates a personalized music personality quiz.

## Features

- **Spotify OAuth Integration**: Secure login with your Spotify account
- **Personalized Quiz**: Questions based on your actual listening data
- **Music Personality Analysis**: Discover your unique music taste profile
- **Personalized Recommendations**: Get song recommendations based on your preferences
- **Beautiful UI**: Modern, responsive design with Spotify branding
- **Share Results**: Share your music personality on social media

## Setup

### Prerequisites

- Python 3.8+
- Spotify Developer Account
- UV package manager (optional, for faster dependency management)

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd listening-history-quiz
   ```

2. **Activate the virtual environment:**
   ```bash
   source bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install flask spotipy python-dotenv requests
   ```

4. **Set up environment variables:**
   The `.env` file is already configured with your Spotify credentials and is included in `.gitignore` for security.

5. **Run the application:**
   ```bash
   python src/app.py
   ```

6. **Open your browser:**
   Navigate to `http://13.56.255.29:3000`

## Spotify App Configuration

To use this app, you need to configure your Spotify app:

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app or use an existing one
3. Add `http://13.56.255.29:3000/callback` to your app's redirect URIs
4. Copy your Client ID and Client Secret to the `.env` file

## How It Works

1. **Authentication**: Users log in with their Spotify account using OAuth 2.0
2. **Data Collection**: The app fetches user's top tracks, artists, and listening history
3. **Quiz Generation**: Personalized questions are created based on the user's data
4. **Analysis**: User answers are combined with Spotify data to generate insights
5. **Results**: Users receive their music personality profile and recommendations

## API Endpoints

- `GET /` - Home page
- `GET /login` - Initiate Spotify OAuth
- `GET /callback` - Handle OAuth callback
- `GET /quiz` - Quiz interface
- `GET /api/quiz-data` - Fetch user's Spotify data
- `POST /submit-quiz` - Process quiz answers
- `GET /results` - Display quiz results

## Security Features

- Environment variables for sensitive data
- Secure OAuth 2.0 flow
- Session management
- Input validation
- CSRF protection

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Spotify API**: Spotipy library
- **Authentication**: Spotify OAuth 2.0
- **Styling**: Custom CSS with Spotify-inspired design

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational purposes. Please respect Spotify's API terms of service.

## Support

If you encounter any issues:
1. Check that your Spotify app is properly configured
2. Ensure all environment variables are set correctly
3. Verify that the redirect URI matches your Spotify app settings
4. Check the console for any error messages

---

Made with ❤️ for music lovers everywhere!
