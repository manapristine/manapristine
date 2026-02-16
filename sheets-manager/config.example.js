# Example configuration - Copy this to config.js and fill in your values

const CONFIG = {
    // Get your API Key from: https://console.cloud.google.com/apis/credentials
    // 1. Create Credentials → API Key
    // 2. Restrict to Google Sheets API and your domain
    API_KEY: 'YOUR_API_KEY_HERE',
    
    // Get your Client ID from: https://console.cloud.google.com/apis/credentials
    // 1. Create Credentials → OAuth client ID
    // 2. Application type: Web application
    // 3. Add authorized JavaScript origins and redirect URIs
    CLIENT_ID: 'YOUR_CLIENT_ID_HERE.apps.googleusercontent.com',
    
    // Your Google Spreadsheet ID (from the URL)
    // Example: https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
    SPREADSHEET_ID: '1Ws6wD6y_sJ47HpQP35VoYXqOEFpeCgKg7AWqTB7XfF4',
    
    // The default sheet name to load
    SHEET_NAME: 'Sheet1',
    
    // Google Sheets API configuration (don't change these)
    DISCOVERY_DOC: 'https://sheets.googleapis.com/$discovery/rest?version=v4',
    SCOPES: 'https://www.googleapis.com/auth/spreadsheets'
};

window.SHEETS_CONFIG = CONFIG;
