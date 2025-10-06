// CCTV Tools JavaScript - Based on original cctv_tool.py functionality

let uploadedDevices = [];
let currentOperation = null;
let operationResults = [];

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
        CommonUtils.showAlert('Failed to load firmware versions', 'error');
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
                if (columns.length >= 4) {
                    devices.push({
                        ip: columns[0].trim(),
                        room: columns[1].trim(),
                        user: columns[2].trim(),
                        userSig: columns[3].trim()
                    });
                }
            }
        }
        
        uploadedDevices = devices;
        CommonUtils.showAlert(`Loaded ${devices.length} devices from CSV`, 'success');
    };
    
    reader.onerror = function() {
        CommonUtils.showAlert('Error reading CSV file', 'error');
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
        
        if (data.status === 'success') {
            operationResults = data.results;
            hideProgressModal();
            showResultsModal('Device Configuration Results', data.results);
        } else {
            hideProgressModal();
            CommonUtils.showAlert('Configuration failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Configuration error:', error);
        hideProgressModal();
        CommonUtils.showAlert('Configuration error: ' + error.message, 'error');
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
        
        if (data.status === 'success') {
            operationResults = data.results;
            hideProgressModal();
            showResultsModal('Firmware Update Results', data.results);
        } else {
            hideProgressModal();
            CommonUtils.showAlert('Firmware update failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Firmware update error:', error);
        hideProgressModal();
        CommonUtils.showAlert('Firmware update error: ' + error.message, 'error');
    }
}

async function checkStatus() {
    if (uploadedDevices.length === 0) {
        CommonUtils.showAlert('Please upload a CSV file with device information first', 'error');
        return;
    }
    
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
        
        if (data.status === 'success') {
            operationResults = data.results;
            hideProgressModal();
            showResultsModal('Device Status Check Results', data.results);
        } else {
            hideProgressModal();
            CommonUtils.showAlert('Status check failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Status check error:', error);
        hideProgressModal();
        CommonUtils.showAlert('Status check error: ' + error.message, 'error');
    }
}

async function rebootDevices() {
    if (uploadedDevices.length === 0) {
        CommonUtils.showAlert('Please upload a CSV file with device information first', 'error');
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
        
        if (data.status === 'success') {
            operationResults = data.results;
            hideProgressModal();
            showResultsModal('Device Reboot Results', data.results);
        } else {
            hideProgressModal();
            CommonUtils.showAlert('Reboot failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Reboot error:', error);
        hideProgressModal();
        CommonUtils.showAlert('Reboot error: ' + error.message, 'error');
    }
}

// =====================
// ✅ Validation
// =====================
function validateOperation() {
    if (uploadedDevices.length === 0) {
        CommonUtils.showAlert('Please upload a CSV file with device information first', 'error');
        return false;
    }
    
    const firmwareVersion = document.getElementById('firmwareVersion').value;
    if (!firmwareVersion) {
        CommonUtils.showAlert('Please select a firmware version', 'error');
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
    
    modal.querySelector('h3').innerHTML = `<i class="fas fa-tasks"></i> ${title}`;
    progressText.textContent = message;
    progressDetails.textContent = 'Preparing operation...';
    progressFill.style.width = '10%';
    
    modal.style.display = 'block';
    
    // Simulate progress
    let progress = 10;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 20;
        if (progress > 90) progress = 90;
        progressFill.style.width = progress + '%';
        
        if (progress > 30 && progress < 60) {
            progressDetails.textContent = `Processing ${uploadedDevices.length} devices...`;
        } else if (progress >= 60) {
            progressDetails.textContent = 'Finalizing operation...';
        }
    }, 500);
    
    // Store interval for cleanup
    modal.progressInterval = progressInterval;
}

function hideProgressModal() {
    const modal = document.getElementById('progressModal');
    if (modal.progressInterval) {
        clearInterval(modal.progressInterval);
    }
    modal.style.display = 'none';
}

function showResultsModal(title, results) {
    const modal = document.getElementById('resultsModal');
    const resultsTitle = document.getElementById('resultsTitle');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsTitle.textContent = title;
    
    if (!results || results.length === 0) {
        resultsContent.innerHTML = '<p style="text-align: center; color: #8b949e;">No results to display</p>';
    } else {
        let html = '';
        results.forEach(result => {
            const statusClass = result.status === 'success' ? 'success' : 
                               result.status === 'error' ? 'error' : 'warning';
            
            html += `
                <div class="result-item ${statusClass}">
                    <div>
                        <div class="result-device">${result.device || result.ip}</div>
                        <div style="color: #8b949e; font-size: 12px;">${result.message}</div>
                    </div>
                    <div class="result-status ${statusClass}">${result.status.toUpperCase()}</div>
                </div>
            `;
        });
        resultsContent.innerHTML = html;
    }
    
    modal.style.display = 'block';
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
        CommonUtils.showAlert('No results to download', 'error');
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
    
    CommonUtils.showAlert('Results downloaded successfully!', 'success');
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