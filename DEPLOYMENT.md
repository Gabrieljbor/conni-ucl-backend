# 🚀 Deploy UCL OAuth Backend for Free

This guide will help you deploy your UCL OAuth backend so anyone can use the "Login with UCL" feature.

## Option 1: Railway (Recommended - Easiest)

### Step 1: Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. Connect your GitHub account

### Step 2: Deploy Your Backend
1. **Push your code to GitHub:**
   ```bash
   cd backend
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/conni-backend.git
   git push -u origin main
   ```

2. **Deploy on Railway:**
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your `conni-backend` repository
   - Railway will automatically detect the Dockerfile and deploy

### Step 3: Configure Environment Variables
In Railway dashboard, go to your project → Variables tab and add:

```env
UCL_CLIENT_ID=your_actual_ucl_client_id
UCL_CLIENT_SECRET=your_actual_ucl_client_secret
SECRET_KEY=your_super_secret_key_here
REDIRECT_URI=https://your-app-name.railway.app/callback
FIREBASE_SERVICE_ACCOUNT={"type":"service_account","project_id":"your-project",...}
```

### Step 4: Get Your Backend URL
- Railway will give you a URL like: `https://your-app-name.railway.app`
- Copy this URL - you'll need it for your React Native app

---

## Option 2: Render (Alternative)

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub

### Step 2: Deploy
1. **Push code to GitHub** (same as Railway)
2. **Create new Web Service:**
   - Connect GitHub repo
   - Choose "Docker" as environment
   - Render will auto-detect Dockerfile

### Step 3: Configure Environment Variables
Same variables as Railway, but use Render's URL format:
```env
REDIRECT_URI=https://your-app-name.onrender.com/callback
```

---

## 🔧 Getting Required Credentials

### UCL API Credentials
1. Go to [uclapi.com](https://uclapi.com)
2. Sign up/login
3. Create a new app
4. Copy `client_id` and `client_secret`

### Firebase Service Account
1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project
3. Go to Project Settings → Service Accounts
4. Click "Generate new private key"
5. Download the JSON file
6. Copy the entire JSON content as a single line string for `FIREBASE_SERVICE_ACCOUNT`

---

## 📱 Update Your React Native App

Once you have your backend URL, update your React Native app:

```javascript
// In assets/pages/login.js
const BACKEND_URL = 'https://your-app-name.railway.app'; // or .onrender.com
```

---

## 🧪 Test Your Deployment

1. **Health Check:**
   Visit `https://your-backend-url.railway.app/health`

2. **Test UCL Login:**
   - Open your React Native app
   - Click "Login with UCL"
   - Complete the OAuth flow
   - Should redirect back to your app

---

## 💰 Cost Breakdown

### Railway
- **Free tier**: $5 credit monthly
- **Usage**: ~$0.50/month for small app
- **Total cost**: FREE (within limits)

### Render
- **Free tier**: 750 hours/month
- **Usage**: ~720 hours/month (always on)
- **Total cost**: FREE

---

## 🚨 Important Notes

1. **HTTPS Required**: OAuth requires HTTPS in production
2. **Domain**: Both platforms provide free HTTPS
3. **Sleep Mode**: Free tiers may sleep after inactivity (Railway doesn't, Render does)
4. **Environment Variables**: Keep your secrets secure!

---

## 🔍 Troubleshooting

### Common Issues

1. **"Firebase not initialized"**
   - Check `FIREBASE_SERVICE_ACCOUNT` environment variable
   - Ensure JSON is properly formatted as single line

2. **"Invalid redirect URI"**
   - Update `REDIRECT_URI` to match your deployed URL
   - Update UCL API settings with new callback URL

3. **App not opening after OAuth**
   - Check URL scheme in `app.json`
   - Ensure deep linking is properly configured

### Debug Commands

```bash
# Check if backend is running
curl https://your-backend-url.railway.app/health

# Test UCL login endpoint
curl https://your-backend-url.railway.app/login/ucl
```

---

## 🎉 You're Done!

Once deployed, anyone with your React Native app can use "Login with UCL" from anywhere in the world!

**Next Steps:**
1. Deploy backend (Railway recommended)
2. Update React Native app with new backend URL
3. Test the complete flow
4. Share your app! 🚀

