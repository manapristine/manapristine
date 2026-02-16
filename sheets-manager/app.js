// Google Sheets Manager - Client-Side Application
// Uses Google Sheets API v4 directly from the browser

// State
let gapiInited = false;
let gisInited = false;
let tokenClient;
let currentData = [];
let currentHeaders = [];
let currentSheet = '';
let editingCell = null;

// DOM Elements
let searchInput, clearSearchBtn, sheetSelect, refreshBtn;
let statusEl, rowCountEl, errorMessageEl;
let loadingEl, tableEl, tableHead, tableBody, noDataEl;
let editModal, editLabel, editInput, saveEditBtn, cancelEditBtn, closeModalBtn;
let authorizeBtn, signoutBtn, authSection, mainContent;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeDOMElements();
    setupEventListeners();
    gapiLoaded();
});

// Get DOM elements
function initializeDOMElements() {
    searchInput = document.getElementById('searchInput');
    clearSearchBtn = document.getElementById('clearSearch');
    sheetSelect = document.getElementById('sheetSelect');
    refreshBtn = document.getElementById('refreshBtn');
    statusEl = document.getElementById('status');
    rowCountEl = document.getElementById('rowCount');
    errorMessageEl = document.getElementById('errorMessage');
    loadingEl = document.getElementById('loading');
    tableEl = document.getElementById('dataTable');
    tableHead = document.getElementById('tableHead');
    tableBody = document.getElementById('tableBody');
    noDataEl = document.getElementById('noData');
    editModal = document.getElementById('editModal');
    editLabel = document.getElementById('editLabel');
    editInput = document.getElementById('editInput');
    saveEditBtn = document.getElementById('saveEdit');
    cancelEditBtn = document.getElementById('cancelEdit');
    closeModalBtn = document.querySelector('.close');
    authorizeBtn = document.getElementById('authorizeBtn');
    signoutBtn = document.getElementById('signoutBtn');
    authSection = document.getElementById('authSection');
    mainContent = document.getElementById('mainContent');
}

// Setup event listeners
function setupEventListeners() {
    searchInput.addEventListener('input', debounce(handleSearch, 300));
    clearSearchBtn.addEventListener('click', clearSearch);
    sheetSelect.addEventListener('change', handleSheetChange);
    refreshBtn.addEventListener('click', loadData);
    saveEditBtn.addEventListener('click', saveEdit);
    cancelEditBtn.addEventListener('click', closeModal);
    closeModalBtn.addEventListener('click', closeModal);
    authorizeBtn.addEventListener('click', handleAuthClick);
    signoutBtn.addEventListener('click', handleSignoutClick);
    
    window.addEventListener('click', (e) => {
        if (e.target === editModal) {
            closeModal();
        }
    });
}

// Load GAPI library
function gapiLoaded() {
    gapi.load('client', initializeGapiClient);
}

// Initialize GAPI client
async function initializeGapiClient() {
    try {
        await gapi.client.init({
            apiKey: window.SHEETS_CONFIG.API_KEY,
            discoveryDocs: [window.SHEETS_CONFIG.DISCOVERY_DOC],
        });
        gapiInited = true;
        maybeEnableButtons();
    } catch (error) {
        console.error('Error initializing GAPI client:', error);
        showError('Failed to initialize Google API. Please check your API key in config.js');
    }
}

// Initialize GIS (Google Identity Services)
function gisLoaded() {
    tokenClient = google.accounts.oauth2.initTokenClient({
        client_id: window.SHEETS_CONFIG.CLIENT_ID,
        scope: window.SHEETS_CONFIG.SCOPES,
        callback: '', // defined later
    });
    gisInited = true;
    maybeEnableButtons();
}

// Enable buttons when both GAPI and GIS are loaded
function maybeEnableButtons() {
    if (gapiInited && gisInited) {
        authorizeBtn.disabled = false;
    }
}

// Handle authorization
function handleAuthClick() {
    tokenClient.callback = async (resp) => {
        if (resp.error !== undefined) {
            showError('Authorization failed: ' + resp.error);
            return;
        }
        
        // Successfully authorized
        authorizeBtn.style.display = 'none';
        signoutBtn.style.display = 'inline-flex';
        authSection.style.display = 'none';
        mainContent.style.display = 'block';
        
        updateStatus('Connected', 'connected');
        await loadSheets();
        await loadData();
    };

    if (gapi.client.getToken() === null) {
        // Prompt the user to select a Google Account and ask for consent
        tokenClient.requestAccessToken({prompt: 'consent'});
    } else {
        // Skip display of account chooser and consent dialog
        tokenClient.requestAccessToken({prompt: ''});
    }
}

// Handle sign out
function handleSignoutClick() {
    const token = gapi.client.getToken();
    if (token !== null) {
        google.accounts.oauth2.revoke(token.access_token);
        gapi.client.setToken('');
        
        authorizeBtn.style.display = 'inline-flex';
        signoutBtn.style.display = 'none';
        authSection.style.display = 'flex';
        mainContent.style.display = 'none';
        
        updateStatus('Not Connected', '');
        currentData = [];
        currentHeaders = [];
    }
}

// Load available sheets
async function loadSheets() {
    try {
        const response = await gapi.client.sheets.spreadsheets.get({
            spreadsheetId: window.SHEETS_CONFIG.SPREADSHEET_ID,
        });
        
        const sheets = response.result.sheets;
        if (sheets && sheets.length > 0) {
            sheetSelect.innerHTML = sheets
                .map(sheet => {
                    const title = sheet.properties.title;
                    return `<option value="${title}">${title}</option>`;
                })
                .join('');
            currentSheet = sheets[0].properties.title;
        }
    } catch (error) {
        console.error('Error loading sheets:', error);
        showError('Failed to load sheets: ' + error.message);
    }
}

// Load data from the current sheet
async function loadData() {
    showLoading();
    hideError();
    
    try {
        const sheet = sheetSelect.value || window.SHEETS_CONFIG.SHEET_NAME;
        const response = await gapi.client.sheets.spreadsheets.values.get({
            spreadsheetId: window.SHEETS_CONFIG.SPREADSHEET_ID,
            range: sheet,
        });
        
        const values = response.result.values;
        
        if (!values || values.length === 0) {
            currentData = [];
            currentHeaders = [];
            renderTable([], []);
            updateRowCount(0);
            hideLoading();
            return;
        }
        
        // First row as headers
        currentHeaders = values[0];
        const rows = values.slice(1);
        
        // Convert to array of objects
        currentData = rows.map((row, index) => {
            const rowData = {_row_index: index + 2}; // +2 because row 1 is headers
            currentHeaders.forEach((header, colIndex) => {
                rowData[header] = row[colIndex] || '';
            });
            return rowData;
        });
        
        renderTable(currentData, currentHeaders);
        updateRowCount(currentData.length);
        hideLoading();
    } catch (error) {
        console.error('Error loading data:', error);
        showError('Failed to load data: ' + error.message);
        hideLoading();
    }
}

// Handle search
function handleSearch() {
    const query = searchInput.value.trim().toLowerCase();
    
    clearSearchBtn.style.display = query ? 'flex' : 'none';
    
    if (query === '') {
        renderTable(currentData, currentHeaders);
        updateRowCount(currentData.length);
        return;
    }
    
    const filtered = currentData.filter(row => {
        return currentHeaders.some(header => {
            const value = String(row[header] || '').toLowerCase();
            return value.includes(query);
        });
    });
    
    renderTable(filtered, currentHeaders);
    updateRowCount(filtered.length, query);
}

// Update a specific cell
async function updateCell(rowIndex, columnName, value) {
    try {
        // Find column index
        const colIndex = currentHeaders.indexOf(columnName);
        if (colIndex === -1) {
            showError('Column not found');
            return false;
        }
        
        // Convert column index to letter
        const colLetter = indexToColumnLetter(colIndex);
        const sheet = sheetSelect.value || window.SHEETS_CONFIG.SHEET_NAME;
        const range = `${sheet}!${colLetter}${rowIndex}`;
        
        await gapi.client.sheets.spreadsheets.values.update({
            spreadsheetId: window.SHEETS_CONFIG.SPREADSHEET_ID,
            range: range,
            valueInputOption: 'RAW',
            resource: {
                values: [[value]]
            }
        });
        
        showSuccess(`Updated ${range}`);
        return true;
    } catch (error) {
        console.error('Error updating cell:', error);
        showError('Update failed: ' + error.message);
        return false;
    }
}

// Convert column index to letter (0 -> A, 25 -> Z, 26 -> AA)
function indexToColumnLetter(index) {
    let letter = '';
    while (index >= 0) {
        letter = String.fromCharCode((index % 26) + 65) + letter;
        index = Math.floor(index / 26) - 1;
    }
    return letter;
}

// Render table
function renderTable(data, headers) {
    if (!data || data.length === 0) {
        tableEl.style.display = 'none';
        noDataEl.style.display = 'block';
        return;
    }
    
    noDataEl.style.display = 'none';
    tableEl.style.display = 'table';
    
    // Render headers
    tableHead.innerHTML = `
        <tr>
            ${headers.map(header => `<th>${escapeHtml(header)}</th>`).join('')}
        </tr>
    `;
    
    // Render rows
    tableBody.innerHTML = data.map(row => {
        const rowIndex = row._row_index;
        return `
            <tr>
                ${headers.map(header => {
                    const value = row[header] || '';
                    return `<td 
                        data-row="${rowIndex}" 
                        data-column="${escapeHtml(header)}"
                        title="Click to edit: ${escapeHtml(value)}"
                    >${escapeHtml(value)}</td>`;
                }).join('')}
            </tr>
        `;
    }).join('');
    
    // Add click handlers to cells
    tableBody.querySelectorAll('td').forEach(cell => {
        cell.addEventListener('click', handleCellClick);
    });
}

// Handle cell click
function handleCellClick(e) {
    const cell = e.target;
    const rowIndex = cell.getAttribute('data-row');
    const columnName = cell.getAttribute('data-column');
    const currentValue = cell.textContent;
    
    openEditModal(rowIndex, columnName, currentValue);
}

// Open edit modal
function openEditModal(rowIndex, columnName, currentValue) {
    editingCell = {rowIndex, columnName, currentValue};
    editLabel.textContent = `Editing: ${columnName} (Row ${rowIndex})`;
    editInput.value = currentValue;
    editModal.style.display = 'block';
    editInput.focus();
    editInput.select();
}

// Close modal
function closeModal() {
    editModal.style.display = 'none';
    editingCell = null;
}

// Save edit
async function saveEdit() {
    if (!editingCell) return;
    
    const newValue = editInput.value;
    
    if (newValue === editingCell.currentValue) {
        closeModal();
        return;
    }
    
    saveEditBtn.disabled = true;
    saveEditBtn.textContent = 'Saving...';
    
    const success = await updateCell(
        editingCell.rowIndex,
        editingCell.columnName,
        newValue
    );
    
    saveEditBtn.disabled = false;
    saveEditBtn.textContent = 'Save';
    
    if (success) {
        closeModal();
        // Refresh data to show updated value
        setTimeout(() => loadData(), 500);
    }
}

// Clear search
function clearSearch() {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    renderTable(currentData, currentHeaders);
    updateRowCount(currentData.length);
}

// Handle sheet change
function handleSheetChange() {
    currentSheet = sheetSelect.value;
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    loadData();
}

// Update status
function updateStatus(text, className) {
    statusEl.textContent = text;
    statusEl.className = 'status ' + className;
}

// Update row count
function updateRowCount(count, query = '') {
    if (query) {
        rowCountEl.textContent = `${count} result${count !== 1 ? 's' : ''} found`;
    } else {
        rowCountEl.textContent = `${count} row${count !== 1 ? 's' : ''}`;
    }
}

// Show loading
function showLoading() {
    loadingEl.style.display = 'block';
    tableEl.style.display = 'none';
    noDataEl.style.display = 'none';
}

// Hide loading
function hideLoading() {
    loadingEl.style.display = 'none';
}

// Show error
function showError(message) {
    errorMessageEl.textContent = message;
    errorMessageEl.style.display = 'block';
}

// Hide error
function hideError() {
    errorMessageEl.style.display = 'none';
}

// Show success message
function showSuccess(message) {
    const successEl = document.createElement('div');
    successEl.className = 'success-message';
    successEl.textContent = message;
    document.body.appendChild(successEl);
    
    setTimeout(() => {
        successEl.style.animation = 'slideOut 0.3s';
        setTimeout(() => successEl.remove(), 300);
    }, 3000);
}

// Utility: debounce
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Utility: escape HTML
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

// Load GIS on window load
window.addEventListener('load', () => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = gisLoaded;
    document.head.appendChild(script);
});
