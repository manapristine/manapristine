# Detailed Setup Guide - Mana Pristine Sheets Manager

This guide will walk you through setting up the Google Sheets Manager step-by-step with screenshots and detailed instructions.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Google Cloud Setup](#google-cloud-setup)
3. [Application Configuration](#application-configuration)
4. [GitHub Pages Deployment](#github-pages-deployment)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, make sure you have:

- ✅ A Google account
- ✅ A GitHub account
- ✅ The spreadsheet URL you want to manage
- ✅ Basic understanding of Git (or use GitHub's web interface)

---

## Google Cloud Setup

### Part 1: Create a Google Cloud Project

**Time Required**: ~5 minutes

1. **Open Google Cloud Console**
   - Go to https://console.cloud.google.com/
   - Sign in with your Google account

2. **Create New Project**
   - Click the project dropdown at the top
   - Click "NEW PROJECT"
   - Enter project name: `Mana Pristine Sheets`
   - Click "CREATE"
   - Wait for project creation (30 seconds)

3. **Enable Google Sheets API**
   - Make sure your new project is selected
   - Go to "APIs & Services" → "Library" (left menu)
   - Search for "Google Sheets API"
   - Click on "Google Sheets API"
   - Click "ENABLE"
   - Wait for activation

### Part 2: Create API Key

**Time Required**: ~2 minutes

1. **Create API Key**
   - Go to "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "API Key"
   - Your API key will be created and shown in a dialog
   - **Copy and save** this key somewhere safe
   - Click "CLOSE"

2. **Restrict API Key (Recommended)**
   - Find your API key in the list
   - Click the edit icon (pencil)
   - Under "API restrictions":
     - Select "Restrict key"
     - Check only "Google Sheets API"
   - Under "Website restrictions":
     - Select "HTTP referrers"
     - Add: `https://YOUR-USERNAME.github.io/*`
     - Replace YOUR-USERNAME with your actual GitHub username
   - Click "SAVE"

### Part 3: Create OAuth 2.0 Client ID

**Time Required**: ~10 minutes

1. **Configure OAuth Consent Screen** (First time only)
   - Go to "APIs & Services" → "OAuth consent screen"
   - Choose "External" user type
   - Click "CREATE"
   
   **App Information:**
   - App name: `Mana Pristine Sheets Manager`
   - User support email: Your email
   - Developer contact: Your email
   - Click "SAVE AND CONTINUE"
   
   **Scopes:**
   - Click "ADD OR REMOVE SCOPES"
   - Filter for "sheets"
   - Check: `https://www.googleapis.com/auth/spreadsheets`
   - Click "UPDATE"
   - Click "SAVE AND CONTINUE"
   
   **Test users:** (Optional for testing)
   - Add your email and any other test users
   - Click "SAVE AND CONTINUE"
   
   **Summary:**
   - Review and click "BACK TO DASHBOARD"

2. **Create OAuth Client ID**
   - Go to "APIs & Services" → "Credentials"
   - Click "CREATE CREDENTIALS" → "OAuth client ID"
   - Application type: "Web application"
   - Name: `Mana Pristine Sheets Web Client`
   
   **Authorized JavaScript origins:**
   - Click "ADD URI"
   - Add: `https://YOUR-USERNAME.github.io`
   - Click "ADD URI"
   - Add: `http://localhost:8000` (for local testing)
   
   **Authorized redirect URIs:**
   - Click "ADD URI"
   - Add: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`
   - Click "ADD URI"
   - Add: `http://localhost:8000/sheets-manager/` (for local testing)
   
   - Click "CREATE"
   - **Copy your Client ID** (looks like: `123456789-abc.apps.googleusercontent.com`)
   - Click "OK"

---

## Application Configuration

### Step 1: Get Your Spreadsheet ID

1. Open your Google Sheet
2. Look at the URL in the browser:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_HERE/edit#gid=0
   ```
3. Copy the `SPREADSHEET_ID_HERE` part
4. For your sheet, it's: `1Ws6wD6y_sJ47HpQP35VoYXqOEFpeCgKg7AWqTB7XfF4`

### Step 2: Update config.js

1. Open the file: `manapristine/sheets-manager/config.js`

2. Replace the placeholder values:

```javascript
const CONFIG = {
    // Replace with your API Key from Google Cloud Console
    API_KEY: 'AIzaSyAbc123def456ghi789jkl012mno345pqr',  // Your actual API Key
    
    // Replace with your OAuth Client ID from Google Cloud Console
    CLIENT_ID: '123456789-abcdefghijklmnopqrstuvwxyz.apps.googleusercontent.com',  // Your actual Client ID
    
    // Your Spreadsheet ID (already configured)
    SPREADSHEET_ID: '1Ws6wD6y_sJ47HpQP35VoYXqOEFpeCgKg7AWqTB7XfF4',
    
    // Change this if your main sheet has a different name
    SHEET_NAME: 'Sheet1',
    
    // Don't change these
    DISCOVERY_DOC: 'https://sheets.googleapis.com/$discovery/rest?version=v4',
    SCOPES: 'https://www.googleapis.com/auth/spreadsheets'
};
```

3. Save the file

### Step 3: Share Your Spreadsheet

**Option A: Public Access (Easiest)**
1. Open your Google Sheet
2. Click "Share" button
3. Change to "Anyone with the link"
4. Set permission to "Viewer" or "Editor"
5. Click "Copy link"
6. Click "Done"

**Option B: Specific Users Only**
1. Open your Google Sheet  
2. Click "Share" button
3. Add email addresses of users who should access the app
4. Set their permissions
5. Click "Send"

---

## GitHub Pages Deployment

### Method 1: Using GitHub Web Interface (Easiest)

1. **Commit Your Changes**
   - Go to your repository on GitHub
   - Navigate to `manapristine/sheets-manager/config.js`
   - Click the edit icon (pencil)
   - Make your changes
   - Scroll down and click "Commit changes"

2. **Enable GitHub Pages**
   - Go to repository "Settings"
   - Click "Pages" in the left sidebar
   - Under "Build and deployment":
     - Source: "Deploy from a branch"
     - Branch: `main` (or `master`)
     - Folder: `/ (root)`
   - Click "Save"

3. **Wait for Deployment**
   - GitHub will build your site (1-2 minutes)
   - Refresh the Pages settings page
   - You'll see: "Your site is live at https://YOUR-USERNAME.github.io/manapristine/"

4. **Access Your App**
   - Navigate to: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`

### Method 2: Using Git Command Line

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/manapristine.git
cd manapristine

# Edit config.js with your credentials
# (Use your preferred editor)
nano sheets-manager/config.js

# Commit and push
git add sheets-manager/config.js
git commit -m "Configure Google Sheets API credentials"
git push origin main

# Enable GitHub Pages in repository settings (as above)
```

---

## Testing

### Test Locally First (Recommended)

1. **Start Local Server**

   Using Python:
   ```bash
   cd manapristine
   python -m http.server 8000
   ```
   
   Or using Node.js:
   ```bash
   npx serve
   ```

2. **Open in Browser**
   - Go to: `http://localhost:8000/sheets-manager/`
   - Click "Sign in with Google"
   - Authorize the application
   - Test browsing, searching, and editing

3. **Check Console for Errors**
   - Press F12 to open Developer Tools
   - Look for any errors in the Console tab
   - Fix any issues before deploying

### Test on GitHub Pages

1. **Access Your Live Site**
   - Go to: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`

2. **Sign In and Test**
   - Click "Sign in with Google"
   - Grant permissions
   - Verify data loads correctly
   - Test search functionality
   - Try editing a cell and saving

---

## Troubleshooting

### Issue: "Failed to initialize Google API"

**Cause**: API Key is incorrect or not configured

**Solution**:
1. Check that `API_KEY` in `config.js` matches your Google Cloud Console API key
2. Verify the API key restrictions allow your domain
3. Make sure Google Sheets API is enabled

### Issue: "Sign in with Google" button does nothing

**Cause**: Client ID is incorrect or redirect URIs don't match

**Solution**:
1. Check that `CLIENT_ID` in `config.js` is correct
2. In Google Cloud Console, verify authorized JavaScript origins include:
   - `https://YOUR-USERNAME.github.io`
3. Verify authorized redirect URIs include:
   - `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`
4. Make sure you're accessing the exact URL (with trailing slash)

### Issue: "Authorization failed" after signing in

**Cause**: OAuth consent screen not configured correctly

**Solution**:
1. Go to Google Cloud Console → OAuth consent screen
2. Make sure status is "In production" or you're added as a test user
3. Verify the scope `https://www.googleapis.com/auth/spreadsheets` is added
4. Try removing and re-adding the scope

### Issue: "Failed to load data"

**Cause**: Spreadsheet not accessible or wrong ID

**Solution**:
1. Verify `SPREADSHEET_ID` in `config.js` is correct
2. Make sure the spreadsheet is shared appropriately
3. Check that you're signed in with an account that has access
4. Verify the sheet name exists in your spreadsheet

### Issue: "Update failed"

**Cause**: No edit permissions or wrong sheet name

**Solution**:
1. Make sure you have edit access to the spreadsheet
2. Verify the sheet name in the dropdown matches the actual sheet
3. Check that OAuth scope includes write permissions

### Issue: GitHub Pages shows 404

**Cause**: Wrong path or Pages not enabled

**Solution**:
1. Verify the URL: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`
2. Check that GitHub Pages is enabled in repository settings
3. Wait 2-3 minutes after enabling for deployment to complete
4. Make sure files are in the correct folder structure

### Issue: CORS errors in console

**Cause**: This shouldn't happen with Google APIs

**Solution**:
1. Make sure you're using `https://` not `http://` for GitHub Pages
2. Clear browser cache and reload
3. Check that you're using the correct API endpoints
4. Verify no browser extensions are blocking requests

---

## Getting Help

If you encounter issues not covered here:

1. **Check Browser Console**
   - Press F12 → Console tab
   - Look for detailed error messages

2. **Verify All Steps**
   - Go through this guide again carefully
   - Double-check all credentials

3. **Test with a Simple Spreadsheet**
   - Create a new test spreadsheet
   - Share it publicly
   - Try accessing it first

4. **Google Cloud Console Quota**
   - Go to "APIs & Services" → "Quotas"
   - Check if you've hit any limits

---

## Security Best Practices

1. ✅ **API Key Restrictions**
   - Always restrict API keys to specific APIs and domains
   - Never use unrestricted keys in production

2. ✅ **OAuth Consent Screen**
   - Use a clear app name and description
   - Only request necessary scopes
   - Keep test user list updated

3. ✅ **Spreadsheet Permissions**
   - Share spreadsheets only with users who need access
   - Use "View only" links when edit access isn't needed
   - Regularly review who has access

4. ✅ **Monitoring**
   - Check Google Cloud Console quotas regularly
   - Monitor API usage
   - Set up alerts for unusual activity

---

## Next Steps

Once everything is working:

1. **Customize the App**
   - Edit `style.css` to match your branding
   - Add custom functionality in `app.js`
   - Update the header text in `index.html`

2. **Add More Features**
   - Data validation
   - Export to CSV/Excel
   - Charts and visualizations
   - Bulk operations

3. **Share with Your Team**
   - Send the GitHub Pages URL
   - Provide sign-in instructions
   - Document any custom workflows

---

**Congratulations!** 🎉 Your Google Sheets Manager is now live on GitHub Pages!
