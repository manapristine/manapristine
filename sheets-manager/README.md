# Mana Pristine Sheets Manager

A client-side web application to browse, search, and update Google Sheets data. Works entirely in the browser with no backend required - perfect for GitHub Pages!

🔗 **Live Demo**: [https://YOUR-USERNAME.github.io/manapristine/sheets-manager/](https://YOUR-USERNAME.github.io/manapristine/sheets-manager/)

## ✨ Features

- 📊 **Browse** - View all spreadsheet data in a beautiful table
- 🔍 **Search** - Real-time search with instant filtering
- ✏️ **Update** - Click any cell to edit and save back to Google Sheets
- 📑 **Multiple Sheets** - Switch between different sheets in your workbook
- 📱 **Responsive** - Works on desktop, tablet, and mobile devices
- 🔐 **Secure** - Uses Google OAuth2 for authentication
- 🚀 **Static** - Runs entirely in the browser, no server needed!

## 🏗️ Architecture

This application uses:
- **Frontend**: Pure HTML, CSS, JavaScript
- **API**: Google Sheets API v4 (client-side)
- **Auth**: Google Identity Services (OAuth2)
- **Hosting**: GitHub Pages (static hosting)

## 🚀 Quick Start

### Option 1: Use GitHub Pages (Recommended)

1. Fork or clone this repository
2. Enable GitHub Pages in repository settings
3. Follow the setup guide below to configure Google API credentials
4. Access your app at: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`

### Option 2: Run Locally

1. Clone the repository
2. Open `index.html` in a web browser
3. Or use a local server:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Node.js
   npx serve
   ```
4. Navigate to `http://localhost:8000/sheets-manager/`

## ⚙️ Setup Guide

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project: "Mana Pristine Sheets"
3. Enable the **Google Sheets API**

### Step 2: Create API Credentials

You need two types of credentials:

#### A. API Key (for reading data)

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **API Key**
3. Copy the API key
4. (Optional) Restrict the key to Google Sheets API and your domain

#### B. OAuth 2.0 Client ID (for writing data)

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Configure consent screen if prompted:
   - User type: External
   - App name: "Mana Pristine Sheets Manager"
   - Add your email
   - Add scopes: `../auth/spreadsheets`
4. Application type: **Web application**
5. Add authorized JavaScript origins:
   - `https://YOUR-USERNAME.github.io`
   - `http://localhost:8000` (for local testing)
6. Add authorized redirect URIs:
   - `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`
   - `http://localhost:8000/sheets-manager/` (for local testing)
7. Click **Create** and copy the Client ID

### Step 3: Configure the Application

Edit `config.js` and add your credentials:

```javascript
const CONFIG = {
    API_KEY: 'YOUR_API_KEY_HERE',
    CLIENT_ID: 'YOUR_CLIENT_ID.apps.googleusercontent.com',
    SPREADSHEET_ID: '1Ws6wD6y_sJ47HpQP35VoYXqOEFpeCgKg7AWqTB7XfF4',
    // ... rest of config
};
```

### Step 4: Share Your Spreadsheet

1. Open your Google Sheet
2. Click the **Share** button
3. Set to "Anyone with the link can view" OR
4. Share with specific Google accounts that will use the app

### Step 5: Deploy to GitHub Pages

1. Commit your changes (with updated `config.js`)
2. Push to GitHub
3. Go to repository **Settings** → **Pages**
4. Source: Deploy from branch `main`
5. Folder: `/ (root)`
6. Save and wait for deployment

Your app will be live at: `https://YOUR-USERNAME.github.io/manapristine/sheets-manager/`

## 🔒 Security Notes

⚠️ **Important Security Information:**

- Client ID and API Key are **public** in client-side code
- This is normal and expected for browser-based apps
- Configure **API key restrictions** in Google Cloud Console:
  - Restrict to Google Sheets API
  - Add HTTP referrers (your GitHub Pages domain)
- OAuth2 ensures only authorized users can edit data
- Never commit service account credentials to public repos

## 📖 Usage

1. **Sign In**: Click "Sign in with Google" button
2. **Authorize**: Grant permissions to access your spreadsheet
3. **Browse**: View all data in the table
4. **Search**: Type in the search box to filter data
5. **Edit**: Click any cell to edit its value
6. **Save**: Changes are saved directly to Google Sheets
7. **Switch Sheets**: Use the dropdown to view different sheets

## 🛠️ Customization

### Change Spreadsheet

Edit `config.js`:
```javascript
SPREADSHEET_ID: 'YOUR_SPREADSHEET_ID',
```

### Styling

Edit `style.css` to customize colors, fonts, and layout.

### Additional Features

Edit `app.js` to add:
- Data validation
- Bulk operations
- Export functionality
- Custom formatting

## 🐛 Troubleshooting

### "Sign in with Google" button doesn't work
- Check that your Client ID is correct in `config.js`
- Verify authorized JavaScript origins in Google Cloud Console
- Make sure you're accessing via HTTPS (GitHub Pages) or localhost

### "Failed to load data" error
- Check that your API Key is correct
- Verify the spreadsheet ID
- Ensure the spreadsheet is shared appropriately
- Check browser console for detailed errors

### Changes not saving
- Verify you've granted spreadsheet edit permissions
- Check that OAuth consent screen includes spreadsheet scope
- Ensure you're signed in with an account that has edit access

### CORS errors
- Client-side apps don't have CORS issues with Google APIs
- If you see CORS errors, check your API configuration
- Ensure you're using the correct API endpoints

## 📚 Resources

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [Google Identity Services](https://developers.google.com/identity/gsi/web)
- [GitHub Pages Documentation](https://docs.github.com/pages)

## 📝 License

MIT License - feel free to use and modify for your needs!

## 🤝 Contributing

Contributions are welcome! Feel free to:
- Report bugs
- Suggest features
- Submit pull requests

---

Made with ❤️ for Mana Pristine community
