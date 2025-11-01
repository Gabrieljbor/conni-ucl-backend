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
        
        # Build the UCL OAuth authorization URL exactly as per documentation
        auth_url = (
            f"https://uclapi.com/oauth/authorise/"
            f"?client_id={UCL_CLIENT_ID}"
            f"&state={state}"
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
        
        # Fetch user data from UCL API
        logger.info(f"Fetching user data from UCL API with token: {access_token[:10]}...")
        
        try:
            user_response = requests.get(
                f'https://uclapi.com/oauth/user/data',
                params={
                    'token': access_token,
                    'client_secret': UCL_CLIENT_SECRET
                },
                timeout=30
            )
            
            if user_response.status_code == 200:
                ucl_user_data = user_response.json()
                logger.info(f"UCL API user data response: {ucl_user_data}")
                
                # Extract user data from UCL API response
                email = ucl_user_data.get('email', '')
                full_name = ucl_user_data.get('full_name', 'UCL Student')
                department = ucl_user_data.get('department', 'Unknown')
                upi = ucl_user_data.get('upi', 'unknown')
                is_student = ucl_user_data.get('is_student', True)
                
                user_data = {
                    'email': email,
                    'is_student': is_student,
                    'full_name': full_name,
                    'department': department,
                    'upi': upi
                }
                
                logger.info(f"Successfully retrieved UCL user data for: {email}")
            else:
                logger.error(f"Failed to get user data from UCL: Status {user_response.status_code}")
                logger.error(f"Response: {user_response.text}")
                return jsonify({'error': f'Failed to get user data from UCL: {user_response.status_code}'}), 400
                
        except requests.RequestException as e:
            logger.error(f"Network error fetching UCL user data: {e}")
            return jsonify({'error': f'Network error: {str(e)}'}), 500
        
        if not email:
            logger.error("No email received from UCL API")
            return jsonify({'error': 'No email received from UCL API'}), 400
        
        # Check if user exists in Firebase/Firestore
        user_info = {
            'email': user_data.get('email'),
            'ucl_data': {
                'department': user_data.get('department', 'Unknown'),
                'full_name': user_data.get('full_name', 'UCL Student'),
                'upi': user_data.get('upi', 'unknown'),
                'is_student': user_data.get('is_student', True),
                'verified_at': datetime.utcnow().isoformat(),
                'auth_method': 'ucl_oauth',
                'token_scope': token_data.get('scope', 'unknown')
            }
        }
        
        if firebase_initialized:
            try:
                # First, check if a UCL user already exists by looking for UCL data in Firestore
                logger.info(f"Looking for existing UCL user with email: {user_data.get('email')}")
                
                # Query Firestore for existing UCL users by email
                # Use the real UCL email to find existing users
                existing_users = db.collection('users').where('email', '==', user_data.get('email')).limit(1).get()
                
                user_id = None
                is_new_user = False
                
                if existing_users:
                    # User exists - get their Firebase UID
                    for doc in existing_users:
                        user_id = doc.id
                        logger.info(f"Found existing user with email {email}: {user_id}")
                        break
                
                if user_id:
                    # Update existing user's UCL data and last login
                    # Ensure existing users are marked as onboarded (they've used the app before)
                    user_ref = db.collection('users').document(user_id)
                    user_ref.update({
                        'ucl_data': user_info['ucl_data'],
                        'last_login': datetime.utcnow(),
                        'ucl_token_scope': token_data.get('scope', 'unknown'),
                        'isOnboarded': True  # Existing users should skip onboarding
                    })
                    logger.info(f"Updated existing UCL user: {user_id}")
                else:
                    # No existing UCL user found - create new one
                    logger.info("No existing UCL user found, creating new user")
                    is_new_user = True
                    
                    # Check if Firebase user exists by email (might be from regular signup)
                    ucl_email = user_data.get('email')
                    try:
                        firebase_user = auth.get_user_by_email(ucl_email)
                        user_id = firebase_user.uid
                        logger.info(f"Found existing Firebase user: {user_id}")
                    except auth.UserNotFoundError:
                        # Create new Firebase user
                        firebase_user = auth.create_user(
                            email=ucl_email,
                            email_verified=True,  # UCL email is considered verified
                            display_name=user_data.get('full_name', 'UCL Student')
                        )
                        user_id = firebase_user.uid
                        logger.info(f"Created new Firebase user: {user_id}")
                    
                    # Create/update user document in Firestore
                    user_ref = db.collection('users').document(user_id)
                    user_ref.set({
                        'email': user_data.get('email'),
                        'display_name': user_data.get('full_name', 'UCL Student'),
                        'ucl_verified': True,
                        'ucl_data': user_info['ucl_data'],
                        'created_at': datetime.utcnow(),
                        'last_login': datetime.utcnow(),
                        'auth_method': 'ucl_oauth',
                        'isOnboarded': False  # New users should go through onboarding
                    }, merge=True)  # merge=True updates existing fields without overwriting
                
                # Generate a custom token for the React Native app
                custom_token = auth.create_custom_token(user_id)
                
                # Redirect back to the app with the custom token
                # For Expo Go, we'll use a different approach
                custom_token_str = custom_token.decode('utf-8')
                
                # Store the token in a way that the app can retrieve it
                # We'll use a simple approach: redirect to a success page with the token
                action = "signup" if is_new_user else "login"
                redirect_url = f"https://conni-ucl-backend-production.up.railway.app/success?token={custom_token_str}&action={action}"
                
                logger.info(f"Redirecting to app with URL: {redirect_url} (action: {action})")
                
                # Return a simple HTML page that tries to open the app
                html_response = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Login Successful</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <style>
                        body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
                        .success {{ color: #4CAF50; }}
                        .instructions {{ margin: 20px 0; }}
                        button {{ background: #836FFF; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
                    </style>
                </head>
                <body>
                    <h1 class="success">✅ Login Successful!</h1>
                    <p>Redirecting to Conni app...</p>
                    <div class="instructions">
                        <button onclick="openApp()">Open Conni App</button>
                    </div>
                    <p><small>If the app doesn't open, please return to the Conni app manually.</small></p>
                    
                    <script>
                        function openApp() {{
                            console.log('Attempting to open app with URL: {redirect_url}');
                            
                            // Try multiple methods to open the app
                            window.location.href = "{redirect_url}";
                            
                            // Also try creating a hidden iframe (for iOS)
                            const iframe = document.createElement('iframe');
                            iframe.style.display = 'none';
                            iframe.src = "{redirect_url}";
                            document.body.appendChild(iframe);
                            
                            // Remove iframe after a short delay
                            setTimeout(() => {{
                                document.body.removeChild(iframe);
                            }}, 1000);
                        }}
                        
                        // Try to open the app immediately
                        setTimeout(openApp, 500);
                        
                        // Show instructions after 5 seconds
                        setTimeout(function() {{
                            document.querySelector('.instructions').innerHTML = `
                                <p><strong>If the app didn't open automatically:</strong></p>
                                <ol style="text-align: left; max-width: 300px; margin: 0 auto;">
                                    <li>Return to the Conni app</li>
                                    <li>You should be logged in automatically</li>
                                    <li>If not, try the UCL login again</li>
                                </ol>
                            `;
                        }}, 5000);
                    </script>
                </body>
                </html>
                """
                
                return html_response
                
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

@app.route('/success')
def success_page():
    """Success page for OAuth callback"""
    token = request.args.get('token')
    action = request.args.get('action', 'login')  # 'login' or 'signup'
    
    if not token:
        return jsonify({'error': 'No token provided'}), 400
    
    action_text = "Welcome back!" if action == "login" else "Welcome to Conni!"
    action_description = "You've successfully logged in with UCL." if action == "login" else "Your UCL account has been created successfully."
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>UCL {action.title()} Successful</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 20px; }}
            .success {{ color: #4CAF50; }}
            .action {{ color: #1E40AF; font-size: 18px; margin: 10px 0; }}
            .token {{ background: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all; font-family: monospace; margin: 10px 0; }}
            .copy-btn {{ 
                background: #836FFF; 
                color: white; 
                border: none; 
                padding: 10px 20px; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 16px;
                margin: 10px 0;
            }}
            .copy-btn:hover {{ background: #6B46C1; }}
            .copied {{ background: #4CAF50 !important; }}
        </style>
    </head>
    <body>
        <h1 class="success">✅ UCL {action.title()} Successful!</h1>
        <p class="action">{action_text}</p>
        <p>{action_description}</p>
        <p><strong>Token:</strong></p>
        <div class="token" id="token">{token}</div>
        <button class="copy-btn" onclick="copyToken()">📋 Copy Token to Clipboard</button>
        <p><small>Copy this token and paste it in the Conni app to complete your {action}.</small></p>
        
        <script>
            function copyToken() {{
                const tokenElement = document.getElementById('token');
                const token = tokenElement.textContent;
                
                navigator.clipboard.writeText(token).then(function() {{
                    const btn = document.querySelector('.copy-btn');
                    const originalText = btn.textContent;
                    btn.textContent = '✅ Copied!';
                    btn.classList.add('copied');
                    
                    setTimeout(function() {{
                        btn.textContent = originalText;
                        btn.classList.remove('copied');
                    }}, 2000);
                }}).catch(function(err) {{
                    console.error('Could not copy text: ', err);
                    alert('Failed to copy token. Please manually select and copy the token above.');
                }});
            }}
            
            // Auto-copy on page load (optional)
            window.onload = function() {{
                setTimeout(function() {{
                    copyToken();
                }}, 1000);
            }};
        </script>
    </body>
    </html>
    """

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

@app.route('/.well-known/apple-app-site-association')
def apple_app_site_association():
    """Serves the Apple App Site Association file."""
    # ⚠️ IMPORTANT: Replace YOUR_TEAM_ID and com.mycompany.conni
    data = {
        "applinks": {
            "details": [
                {
                    "appID": "5ZHL4H672X.com.mycompany.conni",
                    "paths": [ "/success" ]
                }
            ]
        }
    }
    # Flask's jsonify automatically sets Content-Type: application/json
    return jsonify(data)

@app.route('/.well-known/assetlinks.json')
def assetlinks():
    """Serves the Android Asset Links file."""
    # ⚠️ IMPORTANT: Replace com.mycompany.conni and YOUR_SHA256_FINGERPRINT
    data = [
      {
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
          "namespace": "android_app",
          "package_name": "com.mycompany.conni",
          "sha256_cert_fingerprints": ["94:C8:4A:3D:94:8F:60:2B:4C:18:FF:AD:8D:2C:82:6D:33:99:CF:59:2F:F0:44:E6:80:15:56:2B:82:B1:91:30"]
        }
      }
    ]
    return jsonify(data)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
