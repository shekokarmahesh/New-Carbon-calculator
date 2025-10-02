# Carbon Calculator Deployment Guide

This guide explains how to deploy the Carbon Calculator application with the backend on Render and frontend on Vercel.

## 🚀 Deployment Architecture

- **Backend**: Flask API deployed on Render
- **Frontend**: Static site deployed on Vercel
- **Communication**: CORS-enabled API calls

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
3. **GitHub Repository**: Push your code to GitHub

## 🔧 Backend Deployment (Render)

### Step 1: Prepare Backend Files

The following files are already configured:
- `render.yaml` - Render service configuration
- `Procfile` - Process definition
- `requirements.txt` - Python dependencies (includes flask-cors)
- `app.py` - Modified with CORS support

### Step 2: Deploy on Render

1. **Connect GitHub Repository**:
   - Go to [Render Dashboard](https://dashboard.render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure Service**:
   - **Name**: `carbon-calculator-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Plan**: Free tier

3. **Environment Variables** (optional):
   ```
   FLASK_ENV=production
   PYTHON_VERSION=3.11.0
   ```

4. **Deploy**: Click "Create Web Service"

### Step 3: Get Backend URL

After deployment, Render will provide a URL like:
```
https://carbon-calculator-backend.onrender.com
```

**Important**: Update the `backendUrl` in `static/script.js` with your actual Render URL.

## 🌐 Frontend Deployment (Vercel)

### Step 1: Prepare Frontend Files

The following files are already configured:
- `vercel.json` - Vercel configuration
- `package.json` - Node.js configuration
- `static/script.js` - Updated with backend URL

### Step 2: Deploy on Vercel

1. **Connect GitHub Repository**:
   - Go to [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your GitHub repository

2. **Configure Project**:
   - **Framework Preset**: Other
   - **Root Directory**: `./` (root)
   - **Build Command**: `echo 'Static site - no build needed'`
   - **Output Directory**: `./`

3. **Environment Variables** (optional):
   ```
   NEXT_PUBLIC_BACKEND_URL=https://your-backend-url.onrender.com
   ```

4. **Deploy**: Click "Deploy"

### Step 3: Update Backend CORS

After getting your Vercel URL, update the CORS origins in `app.py`:

```python
CORS(app, origins=[
    'https://your-frontend-url.vercel.app',
    'http://localhost:3000'
])
```

Then redeploy the backend on Render.

## 🔄 Development Workflow

### Local Development

1. **Backend**:
   ```bash
   python app.py
   # Runs on http://localhost:5001
   ```

2. **Frontend**:
   ```bash
   python -m http.server 3000
   # Runs on http://localhost:3000
   ```

### Production URLs

- **Backend**: `https://carbon-calculator-backend.onrender.com`
- **Frontend**: `https://carbon-calculator-frontend.vercel.app`

## 🛠️ Troubleshooting

### Common Issues

1. **CORS Errors**:
   - Ensure backend CORS includes your Vercel URL
   - Check that `flask-cors` is in requirements.txt

2. **Backend Not Starting**:
   - Check Render logs for errors
   - Verify all dependencies in requirements.txt
   - Ensure `gunicorn` is installed

3. **Frontend Not Loading**:
   - Check Vercel deployment logs
   - Verify static files are in correct directories
   - Check browser console for errors

### Debugging Steps

1. **Check Backend Health**:
   ```bash
   curl https://your-backend-url.onrender.com/
   ```

2. **Test API Endpoints**:
   ```bash
   curl -X POST https://your-backend-url.onrender.com/calculate \
     -H "Content-Type: application/json" \
     -d '{"project_years": 5, "planting_schedule": []}'
   ```

3. **Check Frontend Console**:
   - Open browser developer tools
   - Look for network errors or CORS issues

## 📝 Notes

- **Free Tier Limits**: Both Render and Vercel free tiers have limitations
- **Cold Starts**: Render free tier may have cold start delays
- **Custom Domains**: Both platforms support custom domains
- **Environment Variables**: Use for different environments (dev/prod)

## 🔗 Useful Links

- [Render Documentation](https://render.com/docs)
- [Vercel Documentation](https://vercel.com/docs)
- [Flask-CORS Documentation](https://flask-cors.readthedocs.io/)
