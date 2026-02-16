# Quick Start Guide

Get your Mana Pristine Sheets Manager up and running in 15 minutes!

## Prerequisites
- Google account
- GitHub account
- The spreadsheet URL you want to manage

## 🚀 5-Minute Setup

### 1. Google Cloud Console (10 minutes)

**Create Project & Enable API:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "Mana Pristine Sheets"
3. Enable "Google Sheets API"

**Get API Key:**
1. Go to Credentials → Create Credentials → API Key
2. Copy the key
3. Restrict to: Google Sheets API + your domain

**Get OAuth Client ID:**
1. Configure OAuth consent screen (External, add your email)
2. Add scope: `https://www.googleapis.com/auth/spreadsheets`
3. Create OAuth Client ID (Web application)
4. Add authorized origin: `https://YOUR-USERNAME.github.io`
5. Add redirect URI: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`
6. Copy the Client ID

### 2. Configure Application (2 minutes)

Edit `config.js`:
```javascript
API_KEY: 'YOUR_API_KEY',
CLIENT_ID: 'YOUR_CLIENT_ID.apps.googleusercontent.com',
SPREADSHEET_ID: '1Ws6wD6y_sJ47HpQP35VoYXqOEFpeCgKg7AWqTB7XfF4',
```

### 3. Deploy to GitHub Pages (3 minutes)

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "Configure Sheets Manager"
   git push
   ```

2. **Enable GitHub Pages:**
   - Repository Settings → Pages
   - Source: main branch
   - Folder: / (root)
   - Save

3. **Access your app:**
   - `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`

## ✅ Test It

1. Open the URL
2. Click "Sign in with Google"
3. Authorize the app
4. Browse your data!
5. Try editing a cell

## 🔧 Local Testing

Before deploying, test locally:

```bash
# Start local server
cd manapristine
python -m http.server 8000

# Open browser
http://localhost:8000/sheets-manager/
```

## 📚 Need More Help?

- [Detailed Setup Guide](./SETUP_GUIDE.md) - Step-by-step with screenshots
- [README](./README.md) - Full documentation
- [Troubleshooting](./SETUP_GUIDE.md#troubleshooting) - Common issues and solutions

## 🎉 That's It!

Your Google Sheets Manager is now live and ready to use!

### What You Can Do:
- ✅ Browse all your data
- ✅ Search and filter records
- ✅ Edit cells directly
- ✅ Switch between sheets
- ✅ Share with your team

### Next Steps:
- Customize the styling in `style.css`
- Add more features in `app.js`
- Share the URL with your team

---

**Having issues?** Check the [Troubleshooting Guide](./SETUP_GUIDE.md#troubleshooting)
