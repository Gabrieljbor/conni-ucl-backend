from flask import Flask, redirect, request, session, jsonify, url_for
import requests
import secrets
import os
from datetime import datetime, timedelta
import json
import logging

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey123')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# UCL API Configuration
UCL_CLIENT_ID = os.environ.get('UCL_CLIENT_ID', 'your_ucl_client_id')
UCL_CLIENT_SECRET = os.environ.get('UCL_CLIENT_SECRET', 'your_ucl_client_secret')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/callback')

# Firebase Admin SDK for user management
try:
    import firebase_admin
    from firebase_admin import credentials, auth, firestore
    from firebase_admin.exceptions import FirebaseError
    
    # Initialize Firebase Admin SDK
    if not firebase_admin._apps:
        # For production, use environment variable for Firebase config
        if os.environ.get('FIREBASE_SERVICE_ACCOUNT'):
            # Parse JSON from environment variable
            firebase_config = json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT'])
            cred = credentials.Certificate(firebase_config)
        else:
            # Fallback to file (for local development)
            cred = credentials.Certificate('firebase-service-account.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    firebase_initialized = True
except ImportError:
    print("Firebase Admin SDK not installed. Install with: pip install firebase-admin")
    firebase_initialized = False
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    firebase_initialized = False

@app.route('/login/ucl')
def login_ucl():
    """Initiate UCL OAuth flow"""
    try:
        # Generate a random state parameter for security
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Build the UCL OAuth authorization URL with proper scopes
        auth_url = (
            f"https://uclapi.com/oauth/authorise"
            f"?client_id={UCL_CLIENT_ID}"
            f"&state={state}"
            f"&scope=user"
        )
        
        return redirect(auth_url)
    except Exception as e:
        return jsonify({'error': f'Failed to initiate UCL login: {str(e)}'}), 500

@app.route('/callback')
def callback():
    """Handle UCL OAuth callback"""
    try:
        result = request.args.get('result')
        code = request.args.get('code')
        state = request.args.get('state')
        
        # Verify the state parameter
        if state != session.get('oauth_state'):
            return jsonify({'error': 'Invalid state parameter'}), 400
        
        # Check if user denied access
        if result != 'allowed':
            return jsonify({'error': 'Access denied by user'}), 403
        
        if not code:
            return jsonify({'error': 'Authorization code not provided'}), 400
        
        # Exchange authorization code for access token
        token_response = requests.post(
            'https://uclapi.com/oauth/token',
            data={
                'client_id': UCL_CLIENT_ID,
                'client_secret': UCL_CLIENT_SECRET,
                'code': code
            },
            timeout=30
        )
        
        if token_response.status_code != 200:
            logger.error(f"Token exchange error: Status {token_response.status_code}")
            logger.error(f"Response: {token_response.text}")
            return jsonify({'error': f'Failed to exchange code for token: {token_response.status_code}'}), 400
        
        token_data = token_response.json()
        logger.info(f"Token response: {token_data}")
        access_token = token_data.get('token')
        
        if not access_token:
            return jsonify({'error': 'No access token received'}), 400
        
        # Get user data from UCL API
        logger.info(f"Making request to UCL API with token: {access_token[:10]}...")
        
        # Try different UCL API endpoints for user data
        endpoints_to_try = [
            'https://uclapi.com/oauth/user/data',
            'https://uclapi.com/oauth/user/me', 
            'https://uclapi.com/oauth/user',
            'https://uclapi.com/user/data',
            'https://uclapi.com/user/me'
        ]
        
        user_response = None
        for endpoint in endpoints_to_try:
            logger.info(f"Trying endpoint: {endpoint}")
            
            # Try with token as query parameter
            user_response = requests.get(
                endpoint,
                params={'token': access_token},
                headers={'User-Agent': 'Conni-App/1.0'},
                timeout=30
            )
            logger.info(f"Response status (query param): {user_response.status_code}")
            if user_response.status_code == 200:
                logger.info(f"Success with endpoint: {endpoint}")
                break
                
            # Try with token as Bearer token
            user_response = requests.get(
                endpoint,
                headers={
                    'User-Agent': 'Conni-App/1.0',
                    'Authorization': f'Bearer {access_token}'
                },
                timeout=30
            )
            logger.info(f"Response status (Bearer): {user_response.status_code}")
            if user_response.status_code == 200:
                logger.info(f"Success with endpoint: {endpoint}")
                break
        
        if user_response.status_code != 200:
            logger.error(f"UCL API Error: Status {user_response.status_code}")
            logger.error(f"Response: {user_response.text}")
            return jsonify({'error': f'Failed to get user data from UCL: {user_response.status_code}'}), 400
        
        user_data = user_response.json()
        
        # Verify user is a student
        if not user_data.get('is_student', False):
            return jsonify({'error': 'Only UCL students can log in via this method'}), 403
        
        email = user_data.get('email')
        if not email:
            return jsonify({'error': 'No email found in UCL user data'}), 400
        
        # Check if user exists in Firebase/Firestore
        user_info = {
            'email': email,
            'ucl_data': {
                'department': user_data.get('department'),
                'full_name': user_data.get('full_name'),
                'upi': user_data.get('upi'),
                'is_student': user_data.get('is_student'),
                'verified_at': datetime.utcnow().isoformat()
            }
        }
        
        if firebase_initialized:
            try:
                # Check if user exists in Firebase Auth
                try:
                    firebase_user = auth.get_user_by_email(email)
                    user_id = firebase_user.uid
                    
                    # Update user document in Firestore with UCL data
                    user_ref = db.collection('users').document(user_id)
                    user_ref.update({
                        'ucl_verified': True,
                        'ucl_data': user_info['ucl_data'],
                        'last_login': datetime.utcnow()
                    })
                    
                except auth.UserNotFoundError:
                    # Create new Firebase user
                    firebase_user = auth.create_user(
                        email=email,
                        email_verified=True,  # UCL email is considered verified
                        display_name=user_data.get('full_name', '')
                    )
                    user_id = firebase_user.uid
                    
                    # Create user document in Firestore
                    user_ref = db.collection('users').document(user_id)
                    user_ref.set({
                        'email': email,
                        'display_name': user_data.get('full_name', ''),
                        'ucl_verified': True,
                        'ucl_data': user_info['ucl_data'],
                        'created_at': datetime.utcnow(),
                        'last_login': datetime.utcnow()
                    })
                
                # Generate a custom token for the React Native app
                custom_token = auth.create_custom_token(user_id)
                
                # Redirect back to the app with the custom token
                app_scheme = "conni"  # Update this to your app's URL scheme
                redirect_url = f"{app_scheme}://ucl-callback?token={custom_token.decode('utf-8')}"
                
                return redirect(redirect_url)
                
            except FirebaseError as e:
                return jsonify({'error': f'Firebase error: {str(e)}'}), 500
        
        else:
            # Fallback if Firebase is not initialized - redirect with error
            app_scheme = "conni"  # Update this to your app's URL scheme
            redirect_url = f"{app_scheme}://ucl-callback?error=Firebase not initialized"
            return redirect(redirect_url)
    
    except requests.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'firebase_initialized': firebase_initialized,
        'ucl_client_id_set': bool(UCL_CLIENT_ID and UCL_CLIENT_ID != 'your_ucl_client_id'),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'message': 'Conni UCL OAuth Backend',
        'endpoints': {
            'login': '/login/ucl',
            'callback': '/callback',
            'health': '/health'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
