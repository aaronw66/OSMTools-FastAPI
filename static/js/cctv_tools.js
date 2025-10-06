// CCTV Tools JavaScript - Based on original cctv_tool.py functionality

let uploadedDevices = [];
let currentOperation = null;
let operationResults = [];

// Create a simple alert function that works for this page
function showAlert(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Create alert element
    const alertDiv = document.createElement('div');
    alertDiv.style.cssText = `
        position: fixed;
        top: 90px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        z-index: 10000;
        max-width: 400px;
        animation: slideIn 0.3s ease;
        font-size: 14px;
        font-weight: 500;
    `;
    alertDiv.textContent = message;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        alertDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => alertDiv.remove(), 300);
    }, 5000);
}

// Add animation styles
if (!document.getElementById('alert-animations')) {
    const style = document.createElement('style');
    style.id = 'alert-animations';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(400px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadFirmwareVersions();
    setupFileUpload();
    setupEventListeners();
});

// =====================
// 🔧 Initialization
// =====================
function setupFileUpload() {
    const fileInput = document.getElementById('csvFile');
    const fileStatus = document.getElementById('fileStatus');
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            fileStatus.textContent = file.name;
            parseCSVFile(file);
        } else {
            fileStatus.textContent = 'No file chosen';
            uploadedDevices = [];
        }
    });
}

function setupEventListeners() {
    // Close modals when clicking outside
    window.addEventListener('click', function(event) {
        const modals = ['progressModal', 'resultsModal'];
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
            closeAllModals();
        }
    });
}

async function loadFirmwareVersions() {
    try {
        const response = await fetch('/cctv-tools/get-firmware-versions');
        const data = await response.json();
        
        const select = document.getElementById('firmwareVersion');
        select.innerHTML = '<option value="">Select firmware version...</option>';
        
        if (data.status === 'success' && data.versions) {
            data.versions.forEach(version => {
                const option = document.createElement('option');
                option.value = version.file;
                option.textContent = version.name;
                select.appendChild(option);
            });
        } else {
            // Add some default versions for development
            const defaultVersions = [
                { file: 'v3.1.2306-1.dingzhi.update', name: 'Version 3.1.2306-1' },
                { file: 'v3.2.2401-2.dingzhi.update', name: 'Version 3.2.2401-2' },
                { file: 'v3.3.2405-1.dingzhi.update', name: 'Version 3.3.2405-1' }
            ];
            
            defaultVersions.forEach(version => {
                const option = document.createElement('option');
                option.value = version.file;
                option.textContent = version.name;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading firmware versions:', error);
        showAlert('Failed to load firmware versions', 'error');
    }
}

// =====================
// 📁 File Handling
// =====================
function parseCSVFile(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        const csv = e.target.result;
        const lines = csv.split('\n');
        const devices = [];
        
        // Skip header row and parse data
        for (let i = 1; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line) {
                const columns = line.split(',');
                // Only add if we have a valid IP address (not empty)
                const ip = columns[0] ? columns[0].trim() : '';
                if (ip && columns.length >= 4) {
                    devices.push({
                        ip: ip,
                        room: columns[1].trim(),
                        user: columns[2].trim(),
                        userSig: columns[3].trim()
                    });
                }
            }
        }
        
        uploadedDevices = devices;
        console.log(`✅ CSV parsed: ${devices.length} devices loaded`);
        console.log('Devices:', devices);
        showAlert(`Loaded ${devices.length} devices from CSV`, 'success');
    };
    
    reader.onerror = function() {
        showAlert('Error reading CSV file', 'error');
    };
    
    reader.readAsText(file);
}

function downloadSample() {
    const sampleCSV = `IP,Room,User,UserSig
192.168.1.100,Room01,user1,signature1
192.168.1.101,Room02,user2,signature2
192.168.1.102,Room03,user3,signature3`;
    
    const blob = new Blob([sampleCSV], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'sample_cctv.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// =====================
// 🎛️ Device Operations
// =====================
async function configureDevices() {
    if (!validateOperation()) return;
    
    currentOperation = 'configure';
    showProgressModal('Configuring Devices', 'Starting device configuration...');
    
    try {
        const response = await fetch('/cctv-tools/configure-devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                devices: uploadedDevices,
                firmware_version: document.getElementById('firmwareVersion').value
            })
        });
        
        const data = await response.json();
        
        // Always hide progress modal before showing results or errors
        hideProgressModal();
        
        if (data.status === 'success') {
            operationResults = data.results;
            // Add small delay to ensure modal closes before showing results
            setTimeout(() => {
                showResultsModal('Device Configuration Results', data.results);
            }, 100);
        } else {
            showAlert('Configuration failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Configuration error:', error);
        hideProgressModal();
        showAlert('Configuration error: ' + error.message, 'error');
    }
}

async function updateFirmware() {
    if (!validateOperation()) return;
    
    currentOperation = 'update';
    showProgressModal('Updating Firmware', 'Starting firmware update...');
    
    try {
        const response = await fetch('/cctv-tools/update-firmware', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                devices: uploadedDevices,
                firmware_version: document.getElementById('firmwareVersion').value
            })
        });
        
        const data = await response.json();
        
        // Always hide progress modal before showing results or errors
        hideProgressModal();
        
        if (data.status === 'success') {
            operationResults = data.results;
            // Add small delay to ensure modal closes before showing results
            setTimeout(() => {
                showResultsModal('Firmware Update Results', data.results);
            }, 100);
        } else {
            showAlert('Firmware update failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Firmware update error:', error);
        hideProgressModal();
        showAlert('Firmware update error: ' + error.message, 'error');
    }
}

async function checkStatus() {
    if (uploadedDevices.length === 0) {
        showAlert('Please upload a CSV file with device information first', 'error');
        return;
    }
    
    console.log(`🚀 Starting status check for ${uploadedDevices.length} devices`);
    console.log('Devices to check:', uploadedDevices);
    
    currentOperation = 'status';
    showProgressModal('Checking Status', 'Checking device status...');
    
    try {
        const response = await fetch('/cctv-tools/check-status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                devices: uploadedDevices
            })
        });
        
        const data = await response.json();
        
        console.log('✅ Check status response:', data);
        console.log(`📊 Results: ${data.results?.length || 0} devices processed`);
        
        // Always hide progress modal before showing results or errors
        hideProgressModal();
        
        if (data.status === 'success') {
            operationResults = data.results;
            console.log('Showing results modal with', data.results.length, 'results');
            // Add small delay to ensure modal closes before showing results
            setTimeout(() => {
                showResultsModal('Device Status Check Results', data.results);
            }, 100);
        } else {
            console.error('Status check failed:', data.message);
            alert('Status check failed: ' + data.message);
        }
    } catch (error) {
        console.error('❌ Status check error:', error);
        hideProgressModal();
        showAlert('Status check error: ' + error.message, 'error');
    }
}

async function rebootDevices() {
    if (uploadedDevices.length === 0) {
        showAlert('Please upload a CSV file with device information first', 'error');
        return;
    }
    
    const confirmed = confirm(`Are you sure you want to reboot ${uploadedDevices.length} device(s)?`);
    if (!confirmed) return;
    
    currentOperation = 'reboot';
    showProgressModal('Rebooting Devices', 'Sending reboot commands...');
    
    try {
        const response = await fetch('/cctv-tools/reboot-devices', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                devices: uploadedDevices
            })
        });
        
        const data = await response.json();
        
        // Always hide progress modal before showing results or errors
        hideProgressModal();
        
        if (data.status === 'success') {
            operationResults = data.results;
            // Add small delay to ensure modal closes before showing results
            setTimeout(() => {
                showResultsModal('Device Reboot Results', data.results);
            }, 100);
        } else {
            showAlert('Reboot failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Reboot error:', error);
        hideProgressModal();
        showAlert('Reboot error: ' + error.message, 'error');
    }
}

// =====================
// ✅ Validation
// =====================
function validateOperation() {
    if (uploadedDevices.length === 0) {
        showAlert('Please upload a CSV file with device information first', 'error');
        return false;
    }
    
    const firmwareVersion = document.getElementById('firmwareVersion').value;
    if (!firmwareVersion) {
        showAlert('Please select a firmware version', 'error');
        return false;
    }
    
    return true;
}

// =====================
// 🎛️ Modal Management
// =====================
function showProgressModal(title, message) {
    const modal = document.getElementById('progressModal');
    const progressText = document.getElementById('progressText');
    const progressDetails = document.getElementById('progressDetails');
    const progressFill = document.getElementById('progressFill');
    const progressStats = document.getElementById('progressStats');
    
    modal.querySelector('h3').textContent = title;
    progressText.textContent = message;
    progressDetails.textContent = 'Starting operation...';
    progressFill.style.width = '0%';
    
    const total = uploadedDevices.length;
    
    // Initialize stats with actual device count
    if (progressStats) {
        progressStats.innerHTML = `
            <div class="stat-item">
                <div class="stat-number" id="statCompleted">0</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-item stat-online">
                <div class="stat-number" id="statOnline">0</div>
                <div class="stat-label">Online</div>
            </div>
            <div class="stat-item stat-offline">
                <div class="stat-number" id="statOffline">0</div>
                <div class="stat-label">Offline</div>
            </div>
            <div class="stat-item stat-remaining">
                <div class="stat-number" id="statRemaining">${total}</div>
                <div class="stat-label">Remaining</div>
            </div>
        `;
    }
    
    modal.style.display = 'block';
    
    // Show indeterminate progress (no fake simulation)
    progressFill.style.width = '100%';
    progressFill.style.animation = 'pulse 1.5s ease-in-out infinite';
    progressText.textContent = `Processing ${total} device${total !== 1 ? 's' : ''}...`;
    progressDetails.textContent = `Checking ${total} device${total !== 1 ? 's' : ''} - please wait`;
    
    console.log(`📊 Progress modal showing: ${total} devices`);
}

function hideProgressModal() {
    const modal = document.getElementById('progressModal');
    const progressFill = document.getElementById('progressFill');
    
    if (modal && modal.progressInterval) {
        clearInterval(modal.progressInterval);
        modal.progressInterval = null;
    }
    
    // Remove animation
    if (progressFill) {
        progressFill.style.animation = 'none';
    }
    
    if (modal) {
        modal.style.display = 'none';
    }
}

function showResultsModal(title, results) {
    console.log('showResultsModal called with title:', title, 'results:', results);
    
    const modal = document.getElementById('resultsModal');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    const resultsSummary = document.getElementById('resultsSummary');
    
    console.log('Modal elements:', { modal, resultsTitle, resultsContent });
    
    if (!modal || !resultsTitle || !resultsContent) {
        console.error('Modal elements not found!');
        return;
    }
    
    resultsTitle.textContent = title;
    
    if (!results || results.length === 0) {
        resultsContent.innerHTML = '<p style="text-align: center; color: #8b949e;">No results to display</p>';
    } else {
        // Calculate summary stats
        const total = results.length;
        const online = results.filter(r => r.status === 'success').length;
        const offline = results.filter(r => r.status === 'error').length;
        
        // Show summary stats
        if (resultsSummary) {
            resultsSummary.innerHTML = `
                <div class="summary-stats">
                    <div class="summary-stat">
                        <div class="summary-number">${total}</div>
                        <div class="summary-label">Total Devices</div>
                    </div>
                    <div class="summary-stat summary-online">
                        <div class="summary-number">${online}</div>
                        <div class="summary-label">Online</div>
                    </div>
                    <div class="summary-stat summary-offline">
                        <div class="summary-number">${offline}</div>
                        <div class="summary-label">Offline</div>
                    </div>
                </div>
                <div class="search-bar">
                    <input type="text" id="resultsSearch" placeholder="Search by IP address..." class="search-input">
                </div>
            `;
            
            // Add search functionality
            setTimeout(() => {
                const searchInput = document.getElementById('resultsSearch');
                if (searchInput) {
                    searchInput.addEventListener('input', (e) => {
                        const searchTerm = e.target.value.toLowerCase();
                        const rows = document.querySelectorAll('.result-table-row');
                        rows.forEach(row => {
                            const ip = row.querySelector('.result-ip')?.textContent.toLowerCase() || '';
                            row.style.display = ip.includes(searchTerm) ? '' : 'none';
                        });
                    });
                }
            }, 100);
        }
        
        // Create detailed table
        let html = `
            <div class="result-table-container">
                <table class="result-table">
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>Status</th>
                            <th>Enable</th>
                            <th>Build Date</th>
                            <th>AppId</th>
                            <th>Room</th>
                            <th>User</th>
                            <th>UserSig</th>
                            <th>Device Name</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        results.forEach(result => {
            const statusClass = result.status === 'success' ? 'online' : 'offline';
            const statusText = result.status === 'success' ? 'ONLINE' : 'OFFLINE';
            const enableText = result.enable !== false ? 'ENABLE' : 'DISABLE';
            const enableClass = result.enable !== false ? 'enabled' : 'disabled';
            
            // Format build date if it's in YYYYMMDD format
            let buildDate = result.build_date || result.firmware || 'Unknown';
            if (buildDate && buildDate.match(/^\d{8}/)) {
                // Extract YYYYMMDD from the firmware string
                const dateMatch = buildDate.match(/(\d{8})/);
                if (dateMatch) {
                    buildDate = dateMatch[1];
                }
            }
            
            html += `
                <tr class="result-table-row">
                    <td class="result-ip">${result.ip || 'N/A'}</td>
                    <td><span class="status-badge status-${statusClass}">${statusText}</span></td>
                    <td><span class="enable-badge enable-${enableClass}">${enableText}</span></td>
                    <td>${buildDate}</td>
                    <td>${result.app_id || '20008185'}</td>
                    <td>${result.room || 'N/A'}</td>
                    <td>${result.user || 'N/A'}</td>
                    <td class="usersig-cell">${result.userSig || result.user_sig || 'hmd5-xxxxx...'}</td>
                    <td>${result.device_name || result.room + '_CCTV (' + result.ip + ')' || 'Unknown'}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        resultsContent.innerHTML = html;
    }
    
    console.log('Setting modal display to block');
    modal.style.display = 'block';
    console.log('Modal display style:', modal.style.display);
}

function closeResultsModal() {
    document.getElementById('resultsModal').style.display = 'none';
}

function closeAllModals() {
    const modals = ['progressModal', 'resultsModal'];
    modals.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
}

// =====================
// 📥 Results Download
// =====================
function downloadResults() {
    if (!operationResults || operationResults.length === 0) {
        showAlert('No results to download', 'error');
        return;
    }
    
    // Create CSV content
    let csvContent = 'Device,IP,Status,Message,Timestamp\n';
    operationResults.forEach(result => {
        const device = result.device || result.ip || 'Unknown';
        const ip = result.ip || '';
        const status = result.status || 'unknown';
        const message = (result.message || '').replace(/,/g, ';'); // Replace commas to avoid CSV issues
        const timestamp = result.timestamp || new Date().toISOString();
        
        csvContent += `"${device}","${ip}","${status}","${message}","${timestamp}"\n`;
    });
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cctv_${currentOperation}_results_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    showAlert('Results downloaded successfully!', 'success');
}

// Export functions for global access
window.CCTVTools = {
    configureDevices,
    updateFirmware,
    checkStatus,
    rebootDevices,
    downloadSample,
    downloadResults,
    closeResultsModal
};