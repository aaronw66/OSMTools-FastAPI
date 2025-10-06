// Image Recon Service JavaScript - Exact functionality from original restart_ir.py

let availableServers = [];
let selectedServers = [];
let currentServerIP = null;
let currentServerHostname = null;
let emailConfig = {};
let searchTimeout = null;
let logsRefreshInterval = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadServers();
    loadEmailSettings();
    setupSearchBox();
    setupEventListeners();
});

// =====================
// 🔍 Search Functionality
// =====================
function setupSearchBox() {
    const searchBox = document.getElementById('searchBox');
    const searchResults = document.getElementById('searchResults');
    
    searchBox.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        // Debounce search
        searchTimeout = setTimeout(() => {
            if (query.length >= 2) {
                performSearch(query);
            } else {
                searchResults.style.display = 'none';
            }
        }, 300);
    });
    
    // Hide search results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchBox.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.style.display = 'none';
        }
    });
}

async function performSearch(query) {
    try {
        const response = await fetch('/image-recon-service/search-machines', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: query })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displaySearchResults(data.results);
        } else {
            console.error('Search failed:', data.message);
        }
    } catch (error) {
        console.error('Search error:', error);
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('searchResults');
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-result-item">No machines found</div>';
        searchResults.style.display = 'block';
        return;
    }
    
    const resultsHTML = results.map(server => `
        <div class="search-result-item" onclick="showLogs('${server.ip}', '${server.hostname}')">
            <div class="search-result-info">
                <div class="search-result-name">${server.hostname}</div>
                <div class="search-result-details">IP: ${server.ip} | Label: ${server.label}</div>
            </div>
            <i class="fas fa-external-link-alt"></i>
        </div>
    `).join('');
    
    searchResults.innerHTML = resultsHTML;
    searchResults.style.display = 'block';
}

// =====================
// 🖥️ Server Management
// =====================
async function loadServers() {
    try {
        const response = await fetch('/image-recon-service/get-servers');
        const data = await response.json();
        
        if (data.status === 'success') {
            availableServers = data.servers;
            displayServers();
            loadServerVersions();
        } else {
            console.error('Failed to load servers:', data.message);
            showError('Failed to load servers: ' + data.message);
        }
    } catch (error) {
        console.error('Error loading servers:', error);
        showError('Error loading servers: ' + error.message);
    }
}

function displayServers() {
    const serverContainer = document.getElementById('server-container');
    
    if (availableServers.length === 0) {
        serverContainer.innerHTML = `
            <div class="loading-state">
                <i class="fas fa-exclamation-triangle"></i>
                <p>No servers available</p>
            </div>
        `;
        return;
    }
    
    // Check if we're showing development/mock data
    const isDevelopment = availableServers.some(server => server.status === 'development');
    
    // Group servers by label
    const serverGroups = {};
    availableServers.forEach(server => {
        const label = server.label || 'Unknown';
        if (!serverGroups[label]) {
            serverGroups[label] = [];
        }
        serverGroups[label].push(server);
    });
    
    let html = '';
    
    if (isDevelopment) {
        html += `
            <div class="dev-notice">
                <div class="dev-notice-content">
                    <span class="dev-notice-icon">🔧</span>
                    <div class="dev-notice-text">
                        <strong>Development Mode</strong><br>
                        Showing mock servers. On production server, real image-recon servers will be loaded.
                    </div>
                </div>
            </div>
        `;
    }
    
    // Generate HTML for each group
    Object.keys(serverGroups).forEach(label => {
        const servers = serverGroups[label];
        
        html += `
            <div class="group-title">
                <i class="fas fa-server"></i> ${label}
            </div>
            <div class="server-box-container">
        `;
        
        servers.forEach(server => {
            const statusClass = server.status === 'development' ? 'unknown' : 'online';
            const devBadge = server.status === 'development' ? '<span class="dev-badge">DEV</span>' : '';
            
            html += `
                <div class="server-box" onclick="showLogs('${server.ip}', '${server.hostname}')" 
                     title="Click to view logs for ${server.hostname}">
                    <i class="fas fa-desktop server-icon"></i>
                    <div class="server-name">${server.hostname} ${devBadge}</div>
                    <div class="server-version" id="version-${server.ip.replace(/\./g, '-')}">Loading...</div>
                    <div class="server-status ${statusClass}">${server.status === 'development' ? 'Development' : 'Online'}</div>
                </div>
            `;
        });
        
        html += '</div>';
    });
    
    serverContainer.innerHTML = html;
}

async function loadServerVersions() {
    // Load all versions at once - matches Flask version exactly
    try {
        const response = await fetch('/image-recon-service/get-all-server-versions');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (data.status === 'success' && data.results) {
            data.results.forEach(result => {
                const versionElement = document.getElementById(`version-${result.ip.replace(/\./g, '-')}`);
                if (versionElement) {
                    // Remove loading class/animation
                    versionElement.classList.remove('loading');
                    
                    if (result.success && result.version !== 'Unknown') {
                        versionElement.textContent = result.version;
                        versionElement.style.background = 'rgba(76, 175, 80, 0.3)';
                        versionElement.style.borderColor = 'rgba(76, 175, 80, 0.6)';
                        versionElement.style.color = '#7ee787';
                    } else {
                        versionElement.textContent = result.version || 'N/A';
                        versionElement.style.background = 'rgba(244, 67, 54, 0.3)';
                        versionElement.style.borderColor = 'rgba(244, 67, 54, 0.6)';
                        versionElement.style.color = '#ff7b72';
                    }
                }
            });
        } else {
            // API returned error - update all Loading... elements to show error
            document.querySelectorAll('.server-version').forEach(el => {
                if (el.textContent === 'Loading...') {
                    el.textContent = 'Error';
                    el.style.background = 'rgba(244, 67, 54, 0.3)';
                    el.style.color = '#ff7b72';
                }
            });
        }
    } catch (error) {
        console.error('Error loading server versions:', error);
        // Update all Loading... elements to show error
        document.querySelectorAll('.server-version').forEach(el => {
            if (el.textContent === 'Loading...') {
                el.textContent = 'Error';
                el.style.background = 'rgba(244, 67, 54, 0.3)';
                el.style.color = '#ff7b72';
            }
        });
    }
}

async function refreshServers() {
    const refreshBtn = document.getElementById('refreshBtn');
    const originalHTML = refreshBtn.innerHTML;
    
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching from servers...';
    refreshBtn.disabled = true;
    
    try {
        // Call backend to fetch IDs from each server via SSH
        const response = await fetch('/image-recon-service/refresh-servers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Reload the server list from the updated ir.json
            await loadServers();
            CommonUtils.showAlert(
                `Server list refreshed! ${data.successful_fetches}/${data.total_servers} servers successful`,
                'success'
            );
        } else {
            CommonUtils.showAlert('Failed to refresh servers: ' + data.message, 'error');
        }
    } catch (error) {
        CommonUtils.showAlert('Failed to refresh servers: ' + error.message, 'error');
    } finally {
        refreshBtn.innerHTML = originalHTML;
        refreshBtn.disabled = false;
    }
}

// =====================
// 📝 Log Management
// =====================
async function showLogs(serverIP, hostname) {
    currentServerIP = serverIP;
    currentServerHostname = hostname;
    
    const modal = document.getElementById('logsModal');
    const serverTitle = document.getElementById('serverTitle');
    const logsContainer = document.getElementById('logs');
    
    serverTitle.textContent = `${hostname} (${serverIP})`;
    logsContainer.innerHTML = `
        <div class="loading-state">
            <i class="fas fa-spinner fa-spin"></i>
            <div>Loading logs...</div>
        </div>
    `;
    
    modal.style.display = 'block';
    
    // Clear any existing refresh interval
    if (logsRefreshInterval) {
        clearInterval(logsRefreshInterval);
    }
    
    // Start auto-refresh every 2.5 seconds (matches Flask version)
    logsRefreshInterval = setInterval(() => {
        loadLogs(serverIP);
    }, 2500);
    
    // Hide search results
    document.getElementById('searchResults').style.display = 'none';
    document.getElementById('searchBox').value = '';
    
    // Load logs
    await loadLogs(serverIP);
}

async function loadLogs(serverIP, lines = 50) {
    try {
        const response = await fetch('/image-recon-service/get-logs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                server_ip: serverIP,
                lines: lines 
            })
        });
        
        const data = await response.json();
        const logsContainer = document.getElementById('logs');
        
        if (data.status === 'success') {
            logsContainer.textContent = data.logs;
        } else {
            logsContainer.innerHTML = `
                <div style="color: #ff7b72; text-align: center; padding: 20px;">
                    <i class="fas fa-exclamation-triangle"></i><br>
                    ${data.message}
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading logs:', error);
        const logsContainer = document.getElementById('logs');
        logsContainer.innerHTML = `
            <div style="color: #ff7b72; text-align: center; padding: 20px;">
                <i class="fas fa-exclamation-triangle"></i><br>
                Error loading logs: ${error.message}
            </div>
        `;
    }
}

async function refreshLogs() {
    if (currentServerIP) {
        await loadLogs(currentServerIP);
    }
}

async function restartService() {
    if (!currentServerIP || !currentServerHostname) return;
    
    const confirmed = confirm('Are you sure you want to restart the service on this server?');
    if (!confirmed) return;
    
    try {
        const response = await fetch('/image-recon-service/restart-service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                servers: [{ 
                    ip: currentServerIP,
                    hostname: currentServerHostname,
                    label: currentServerHostname.split('-')[0]
                }],
                service_name: 'osm'
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showMessage('Service restart initiated successfully!', 'success');
            // Refresh logs after a delay
            setTimeout(() => refreshLogs(), 3000);
        } else {
            showMessage('Failed to restart service: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error restarting service:', error);
        showMessage('Error restarting service: ' + error.message, 'error');
    }
}

// =====================
// 📧 Email Management
// =====================
async function loadEmailSettings() {
    try {
        const response = await fetch('/image-recon-service/get-email-settings');
        const data = await response.json();
        
        if (data.status === 'success') {
            emailConfig = data.config;
        }
    } catch (error) {
        console.error('Error loading email settings:', error);
    }
}

function showEmailModal() {
    const modal = document.getElementById('emailModal');
    modal.style.display = 'block';
    displayEmailRecipients();
}

function displayEmailRecipients() {
    const recipientsList = document.getElementById('recipientsList');
    
    if (!emailConfig.recipients || emailConfig.recipients.length === 0) {
        recipientsList.innerHTML = '<p style="color: #8b949e;">No recipients configured</p>';
        return;
    }
    
    const recipientsHTML = emailConfig.recipients.map(email => `
        <div class="recipient-item">
            <span class="recipient-email">${email}</span>
            <button class="remove-recipient" onclick="removeEmailRecipient('${email}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
    
    recipientsList.innerHTML = recipientsHTML;
}

async function addEmailRecipient() {
    const emailInput = document.getElementById('newRecipientEmail');
    const email = emailInput.value.trim();
    
    if (!email) {
        CommonUtils.showAlert('Please enter an email address', 'error');
        return;
    }
    
    if (!isValidEmail(email)) {
        CommonUtils.showAlert('Please enter a valid email address', 'error');
        return;
    }
    
    try {
        const response = await fetch('/image-recon-service/add-email-recipient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            emailInput.value = '';
            await loadEmailSettings();
            displayEmailRecipients();
            CommonUtils.showAlert('Email recipient added successfully!', 'success');
        } else {
            CommonUtils.showAlert('Failed to add recipient: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error adding email recipient:', error);
        CommonUtils.showAlert('Error adding recipient: ' + error.message, 'error');
    }
}

async function removeEmailRecipient(email) {
    const confirmed = confirm(`Remove ${email} from recipients?`);
    if (!confirmed) return;
    
    try {
        const response = await fetch('/image-recon-service/remove-email-recipient', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: email })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            await loadEmailSettings();
            displayEmailRecipients();
            CommonUtils.showAlert('Email recipient removed successfully!', 'success');
        } else {
            CommonUtils.showAlert('Failed to remove recipient: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error removing email recipient:', error);
        CommonUtils.showAlert('Error removing recipient: ' + error.message, 'error');
    }
}

async function sendTestEmail() {
    const messageInput = document.getElementById('testEmailMessage');
    const message = messageInput.value.trim() || 'This is a test email from Image Recon Service Manager.';
    
    try {
        const response = await fetch('/image-recon-service/send-batch-email', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                recipients: emailConfig.recipients,
                subject: 'Test Email - Image Recon Service Manager',
                message: message
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            CommonUtils.showAlert('Test email sent successfully!', 'success');
            messageInput.value = '';
        } else {
            CommonUtils.showAlert('Failed to send test email: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error sending test email:', error);
        CommonUtils.showAlert('Error sending test email: ' + error.message, 'error');
    }
}

// =====================
// 🔄 Batch Update Operations
// =====================
function showUpdateModal() {
    const modal = document.getElementById('updateModal');
    modal.style.display = 'block';
    populateUpdateServerList();
}

function populateUpdateServerList() {
    const serverList = document.getElementById('updateServerList');
    
    if (availableServers.length === 0) {
        serverList.innerHTML = '<p style="color: #8b949e;">No servers available</p>';
        return;
    }
    
    const serversHTML = availableServers.map((server, index) => `
        <div class="server-checkbox-item">
            <input type="checkbox" id="update-server-${index}" value="${index}">
            <label for="update-server-${index}" class="server-checkbox-label">
                ${server.hostname} (${server.ip})
            </label>
        </div>
    `).join('');
    
    serverList.innerHTML = serversHTML;
}

async function startBatchUpdate() {
    const checkboxes = document.querySelectorAll('#updateServerList input[type="checkbox"]:checked');
    const selectedServerIndices = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    if (selectedServerIndices.length === 0) {
        CommonUtils.showAlert('Please select at least one server', 'error');
        return;
    }
    
    const selectedServers = selectedServerIndices.map(index => availableServers[index]);
    const updateFile = document.getElementById('updateFile').files[0];
    
    const confirmed = confirm(`Start batch update on ${selectedServers.length} server(s)?`);
    if (!confirmed) return;
    
    closeUpdateModal();
    showProgressModal();
    
    try {
        const response = await fetch('/image-recon-service/start-update-process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                servers: selectedServers,
                update_file: updateFile ? updateFile.name : null
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            displayUpdateResults(data.results);
        } else {
            hideProgressModal();
            CommonUtils.showAlert('Batch update failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error starting batch update:', error);
        hideProgressModal();
        CommonUtils.showAlert('Error starting batch update: ' + error.message, 'error');
    }
}

function displayUpdateResults(results) {
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    const progressFill = document.getElementById('progressFill');
    
    progressText.textContent = 'Update Complete';
    progressFill.style.width = '100%';
    
    let detailsHTML = '<h4>Update Results:</h4>';
    results.forEach(result => {
        const statusIcon = result.status === 'success' ? '✅' : '❌';
        detailsHTML += `<div>${statusIcon} ${result.hostname}: ${result.message}</div>`;
    });
    
    progressDetails.innerHTML = detailsHTML;
    
    // Auto-close after 10 seconds
    setTimeout(() => {
        hideProgressModal();
    }, 10000);
}

// =====================
// 🎛️ Modal Management
// =====================
function closeModal() {
    // Stop auto-refresh
    if (logsRefreshInterval) {
        clearInterval(logsRefreshInterval);
        logsRefreshInterval = null;
    }
    
    document.getElementById('logsModal').style.display = 'none';
    currentServerIP = null;
    currentServerHostname = null;
}

function closeMessageModal() {
    document.getElementById('messageModal').style.display = 'none';
}

function closeUpdateModal() {
    document.getElementById('updateModal').style.display = 'none';
}

function closeEmailModal() {
    document.getElementById('emailModal').style.display = 'none';
}

function showProgressModal() {
    const modal = document.getElementById('progressModal');
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    const progressFill = document.getElementById('progressFill');
    
    progressText.textContent = 'Starting update process...';
    progressDetails.textContent = 'Preparing servers...';
    progressFill.style.width = '0%';
    
    modal.style.display = 'block';
}

function hideProgressModal() {
    document.getElementById('progressModal').style.display = 'none';
}

function showMessage(message, type = 'info') {
    const modal = document.getElementById('messageModal');
    const messageContainer = document.getElementById('message');
    
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    messageContainer.innerHTML = `<div style="text-align: center; padding: 20px;"><h3>${icon}</h3><p>${message}</p></div>`;
    
    modal.style.display = 'block';
}

function showError(message) {
    showMessage(message, 'error');
}

// =====================
// 🛠️ Utility Functions
// =====================
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

function setupEventListeners() {
    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        const modals = ['logsModal', 'messageModal', 'updateModal', 'emailModal', 'progressModal'];
        modals.forEach(modalId => {
            const modal = document.getElementById(modalId);
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            // Close any open modal
            const modals = ['logsModal', 'messageModal', 'updateModal', 'emailModal'];
            modals.forEach(modalId => {
                const modal = document.getElementById(modalId);
                if (modal.style.display === 'block') {
                    modal.style.display = 'none';
                }
            });
            
            // Hide search results
            document.getElementById('searchResults').style.display = 'none';
        }
    });
}

// Export functions for global access
window.ImageReconService = {
    loadServers,
    refreshServers,
    showLogs,
    restartService,
    showEmailModal,
    showUpdateModal,
    closeModal,
    closeMessageModal,
    closeUpdateModal,
    closeEmailModal
};