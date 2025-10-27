# UCL OAuth Integration for Conni App

This backend provides UCL OAuth integration for the Conni React Native app, allowing UCL students to log in using their university credentials.

## Features

- ✅ UCL OAuth flow implementation
- ✅ Student verification (only UCL students can log in)
- ✅ Firebase integration for user management
- ✅ Custom token generation for React Native app
- ✅ Deep linking support for seamless authentication

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- UCL API credentials (get from https://uclapi.com/)
- Firebase project with service account key

### 2. Quick Setup

```bash
cd backend
python setup.py
```

### 3. Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

3. **Add Firebase service account:**
   - Download `firebase-service-account.json` from Firebase Console
   - Place it in the backend directory

4. **Get UCL API credentials:**
   - Visit https://uclapi.com/
   - Create an account and register your app
   - Copy `client_id` and `client_secret` to `.env`

### 4. Environment Variables

Create a `.env` file with the following variables:

```env
# UCL API Credentials
UCL_CLIENT_ID=your_ucl_client_id_here
UCL_CLIENT_SECRET=your_ucl_client_secret_here

# Backend Configuration
SECRET_KEY=your_super_secret_key_here
REDIRECT_URI=http://localhost:5000/callback
```

### 5. Running the Backend

```bash
python app.py
```

The server will start on `http://localhost:5000`

## API Endpoints

- `GET /login/ucl` - Initiates UCL OAuth flow
- `GET /callback` - Handles OAuth callback
- `GET /health` - Health check endpoint

## OAuth Flow

1. User clicks "Login with UCL" in the app
2. App opens browser to `/login/ucl`
3. User logs in via UCL SSO
4. UCL redirects to `/callback` with authorization code
5. Backend exchanges code for access token
6. Backend verifies user is a UCL student
7. Backend creates/updates Firebase user
8. Backend redirects back to app with custom token
9. App signs in user with custom token

## React Native Integration

The React Native app needs to:

1. Handle deep linking for OAuth callback
2. Configure URL scheme in `app.json`:
   ```json
   {
     "expo": {
       "scheme": "conni"
     }
   }
   ```

3. Update `BACKEND_URL` in login screen to point to your backend

## Security Notes

- State parameter is used to prevent CSRF attacks
- Only verified UCL students can log in
- Custom tokens are used for secure Firebase authentication
- Environment variables should be kept secure

## Troubleshooting

### Common Issues

1. **"Firebase not initialized"**
   - Ensure `firebase-service-account.json` is in the backend directory
   - Check Firebase project configuration

2. **"Only UCL students can log in"**
   - User is not a current UCL student
   - UCL API data doesn't show `is_student: true`

3. **Deep linking not working**
   - Check URL scheme configuration in `app.json`
   - Ensure backend redirect URL matches app scheme

### Debug Mode

Run with debug logging:
```bash
FLASK_DEBUG=1 python app.py
```

## Production Deployment

For production deployment:

1. Use a production WSGI server (gunicorn)
2. Set up proper environment variables
3. Configure HTTPS
4. Update `REDIRECT_URI` to production URL
5. Update `BACKEND_URL` in React Native app

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```


